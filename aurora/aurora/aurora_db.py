# mySQL Database Functions
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Collection of methods for adding, updating, deleting, and querying the database
"""

import datetime
import json
import logging
import os
from pprint import pprint
import sys
import traceback
from types import *

import MySQLdb as mdb

from aurora.cls_logger import get_cls_logger
from aurora.exc import *

LOGGER = logging.getLogger(__name__)


class AuroraDB(object):
    #Default values in __init__ should potentially be omitted

    DEFAULT_MYSQL_HOST = 'localhost'
    DEFAULT_MYSQL_USERNAME = 'root'
    DEFAULT_MYSQL_PASSWORD = 'supersecret'
    DEFAULT_MYSQL_DB = 'aurora'

    def __init__(self,
                 mysql_host = DEFAULT_MYSQL_HOST,
                 mysql_username = DEFAULT_MYSQL_USERNAME,
                 mysql_password = DEFAULT_MYSQL_PASSWORD,
                 mysql_db = DEFAULT_MYSQL_DB):
        """Create a new instance of AuroraDB object.

        :param str mysql_host:
        :param str mysql_username:
        :param str mysql_password:
        :param str mysql_db:

        """
        self.LOGGER = get_cls_logger(self)

        self.LOGGER.info("Constructing AuroraDB...")

        self.mysql_host = mysql_host
        self.mysql_username = mysql_username
        self.mysql_password = mysql_password
        self.mysql_db = mysql_db

    def __del__(self):
        self.LOGGER.info("Destructing AuroraDB...")

    def _database_connection(self):
        """Returns a handle for MySQL database access using 
        credentials assigned when AuroraDB instance was created.

        :rtype: MySQLdb.Connection()

        """
        return mdb.connect(self.mysql_host, self.mysql_username,
                           self.mysql_password, self.mysql_db)

    def _count_db_slices(self, radio_list):
        """Counts the number of slices in given a radio config

        :returns: int - Number of slices

        """
        current_slices = 0
        for radio in radio_list:
            current_slices += len(radio["bss_list"])
        return current_slices

    def ap_add(self, ap_name):
        """Adds an access point to the MySQL database.

        :param str ap_name:
        :raises: InvalidAPNameType

        """
        self.LOGGER.info("Adding ap %s to database", ap_name)
        self.LOGGER.info("type(ap_name) %s", type(ap_name))
        if (ap_name is None or 
                (type(ap_name) is not StringType and
                 type(ap_name) is not UnicodeType)
           ):
            raise InvalidAPNameType()
        try:
            with self._database_connection() as db:
                db.execute("""INSERT INTO ap SET name='%s'""" % ap_name)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_status_up(self, ap_name=None):
        """Sets the status of an access point to 'UP'.

        :param str ap_name:
        :raises: NoAPNameGivenException

        """
        if ap_name == None:
            raise NoAPNameGivenException()
        self.LOGGER.info("Setting %s status 'UP'", ap_name)
        try:
            with self._database_connection() as db:
                db.execute("UPDATE ap SET status='UP' WHERE name='%s'" %
                                (ap_name))
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_status_down(self, ap_name=None):
        """Sets the status of an access point to 'DOWN'.

        :param str ap_name:
        :raises: NoAPNameGivenException

        """
        if ap_name == None:
            raise NoAPNameGivenException()
        self.LOGGER.info("Setting %s status 'DOWN'", ap_name)
        try:
            with self._database_connection() as db:
                db.execute("UPDATE ap SET status='DOWN' WHERE name='%s'" %
                                (ap_name))
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_status_unknown(self, ap_name=None):
        """Sets the status of an access point to 'UNKNOWN'.
        This will occur when the manager has shut down and 
        is no longer polling the APs, though they could
        still be active.

        :param str ap_name:

        """
        try:
            with self._database_connection() as db:
                if ap_name is None:
                    db.execute("UPDATE ap SET status='UNKNOWN'")
                else:
                    db.execute("UPDATE ap SET status='UNKNOWN' WHERE name='%s'" %
                                    (ap_name))

        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def _get_time_format(self, time):
        """Helper method to create a standardized time format.
        Input parameter is a :clsas:`datetime.timedelta`.

        :param :class:`datetime.timedelta` time:
        :rtype: str

        """
        time = time.total_seconds()
        hours = int(time // 3600)
        time = time - hours * 3600
        minutes = int(time // 60)
        time = time - minutes * 60
        seconds = int(time)
        microseconds = int((time - seconds) * 1000000)
        time_format = '%s:%s:%s.%s' % (str(hours), str(minutes), str(seconds), str(microseconds))
        return time_format

    def ap_slice_set_physical_ap(self, ap_slice_id, ap_name):
        """Sets the physical_ap column entry for a slice.

        :param str ap_slice_id:
        :param str ap_name:

        """
        try:
            with self._database_connection() as db:
                db.execute(
                    """UPDATE ap_slice SET
                               physical_ap='%s'
                           WHERE ap_slice_id='%s'""" %
                       (ap_name, ap_slice_id)
                )
        except Exception, e:
            traceback.print_exc(file=sys.stdout)


    def ap_slice_update_time_stats(self, ap_slice_id=None, ap_name=None, ap_down=False):
        """Records the current time and calculates current and
        cumulative uptime for a slice on an access point.

        If the slice ID is the only parameter given, only that
        slice is updated.  Otherwise, all the slices on the
        access point in question will be updated.

        .. note::

            This method does not check the status of the slices
            it is passed.  You must make sure they are candidates
            for metering before calling this method.

        :param str ap_slice_id: ID of the slice to update
        :param str ap_name: Name of the access point where the
                            slice resides

        """
        self.LOGGER.debug("Updating time stats for %s", (ap_slice_id or ap_name))
        if ap_name is not None:
            slice_list = self.get_physical_ap_slices(ap_name)
        else:
            slice_list = [ap_slice_id]
        self.LOGGER.debug("slice list: %s", slice_list)
        for s_id in slice_list:
            try:
                with self._database_connection() as db:
                    db.execute("SELECT last_time_activated, last_time_updated, total_active_duration FROM metering WHERE ap_slice_id='%s'" % s_id)
                    previous_time_stats = db.fetchone()
                    self.LOGGER.debug("previous_time_stats: %s", previous_time_stats)
                    time_active = None
                    now = datetime.datetime.now()
                    (last_time_activated, last_time_updated,
                     current_active_duration, total_active_duration) = (None, None, None, None)
                    if previous_time_stats is not None:
                        (last_time_activated, last_time_updated, total_active_duration) = previous_time_stats
                    if last_time_activated is None and ap_down:
                        # Slice was never activated and ap didn't respond, don't update stats
                        continue
                        
                    if last_time_activated is None:
                        self.LOGGER.warn("No value for last time activated for slice %s", s_id)
                        self.LOGGER.info("Setting last time activated %s", now)
                        to_execute = ("""UPDATE metering SET
                                             last_time_activated='%s'
                                             WHERE ap_slice_id='%s'""" %
                                         (now, s_id)
                                     )
                        last_time_activated = now
                    else:
                        current_active_duration = self._get_time_format(now - last_time_activated)
                        to_execute = ("""UPDATE metering SET 
                                             current_active_duration='%s'
                                             WHERE ap_slice_id='%s'""" % 
                                             (current_active_duration, s_id)
                                     )
                    self.LOGGER.debug(to_execute)
                    db.execute(to_execute)
                    if last_time_updated is None:
                        self.LOGGER.warn("No value for last time updated for slice %s", s_id)
                        self.LOGGER.info("Using value for last time activated %s", last_time_activated)
                        last_time_updated = last_time_activated

                    time_diff = now - last_time_updated
                    total_active_duration = self._get_time_format(total_active_duration + time_diff)
                    to_execute = ("""UPDATE metering SET 
                                         total_active_duration='%s',
                                         last_time_updated='%s'
                                         WHERE ap_slice_id='%s'""" % 
                                         (total_active_duration, now, s_id)
                                 )
                    self.LOGGER.debug(to_execute)
                    db.execute(to_execute)

            except Exception:
                traceback.print_exc(file=sys.stdout)
                #self.LOGGER.error("Error: %s", str(e))

    def ap_slice_update_mb_sent(self, ap_slice_id, mb_sent):
        """Updates the metering traffic log for a specific slice.

        :param str ap_slice_id:
        :param float mb_sent:

        """
        try:
            with self._database_connection() as db:
                to_execute = ("""UPDATE metering SET 
                                     total_mb_sent=
                                         (total_mb_sent-current_mb_sent)
                                             + %s,
                                     current_mb_sent=
                                         %s
                                     WHERE ap_slice_id='%s'""" %
                                 (mb_sent, mb_sent, ap_slice_id)
                             )
                self.LOGGER.debug(to_execute)
                db.execute(to_execute)
        except Exception:
            traceback.print_exc(file=sys.stdout)

    def ap_update_hw_info(self, hw_database, ap_name, region):
        """Given a hardware database report from an access
        point, updates information in MySQL DB to remain
        current.  Obvious update criteria are free disk
        space and number_slice_free.

        :param dict hw_database: Database containing all
                                 hardware info for a given
                                 access point
        :param str ap_name: Access point name to associated
                            with hardware info
        :param str region: Region where the access point is located

        """
        try:
            with self._database_connection() as db:
                firmware = hw_database["firmware"]
                firmware_version = hw_database["firmware_version"]
                number_radio = hw_database["wifi_radio"]["number_radio"]
                memory_mb = hw_database["memory_mb"]
                free_disk = hw_database["free_disk"]
                number_radio_free = hw_database["wifi_radio"]["number_radio_free"]
                max_available_slices = int(hw_database["wifi_radio"]["max_bss_per_radio"])*int(number_radio)
                current_slices = self._count_db_slices(hw_database["wifi_radio"]["radio_list"])
                number_slice_free = int(max_available_slices) - current_slices

                to_execute = (
                    """INSERT INTO ap SET 
                               name='%s', region='%s', firmware='%s', 
                               version='%s', number_radio=%s, 
                               memory_mb=%s, free_disk=%s, 
                               number_radio_free=%s, number_slice_free=%s, status='UP'
                           ON DUPLICATE KEY UPDATE 
                               name='%s', region='%s', firmware='%s', 
                               version='%s', number_radio=%s, 
                               memory_mb=%s, free_disk=%s, 
                               number_radio_free=%s, number_slice_free=%s""" %
                       (ap_name, region, firmware,
                       firmware_version, number_radio,
                       memory_mb, free_disk,
                       number_radio_free, number_slice_free,
                       ap_name, region, firmware,
                       firmware_version, number_radio,
                       memory_mb, free_disk,
                       number_radio_free, number_slice_free,
                       )
                )

                self.LOGGER.debug(to_execute)
                db.execute(to_execute)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_slice_status_up(self, ap_slice_id):
        """Sets status to 'ACTIVE' for given ap_slice_id.

        :param str ap_slice_id: Slice ID to set
        :raises: InvalidACTIVEStatusUpdate

        """
        try:
            with self._database_connection() as db:
                num_results = db.execute("SELECT status FROM ap_slice WHERE ap_slice_id='%s'" % ap_slice_id)
                status = None

                if num_results == 1:
                    status = db.fetchone()[0]
                    if (status != 'ACTIVE' and
                            status != 'PENDING' and
                            status != 'DOWN'):
                        raise InvalidACTIVEStatusUpdate(status=status)

                    self.LOGGER.info("Setting status 'ACTIVE' for %s", ap_slice_id)
                    to_execute = ("UPDATE ap_slice SET "
                                          "status='ACTIVE' "
                                      "WHERE ap_slice_id='%s'" % ap_slice_id)
                    self.LOGGER.debug(to_execute)
                    db.execute(to_execute)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_slice_status_pending(self, ap_slice_id):
        """Sets status to 'PENDING' for given ap_slice_id.

        :param str ap_slice_id: Slice ID to set
        :raises: InvalidPENDINGStatusUpdate

        """
        try:
            with self._database_connection() as db:
                num_results = db.execute("SELECT status FROM ap_slice WHERE ap_slice_id='%s'" % ap_slice_id)
                status = None

                if num_results == 1:
                    status = db.fetchone()[0]
                    if (status != 'ACTIVE' and
                            status != 'FAILED'):
                        raise InvalidPENDINGStatusUpdate(status=status)

                    self.LOGGER.info("Setting status 'PENDING' for %s", ap_slice_id)
                    to_execute = ("UPDATE ap_slice SET "
                                          "status='PENDING' "
                                      "WHERE ap_slice_id='%s'" % ap_slice_id)
                    self.LOGGER.debug(to_execute)
                    db.execute(to_execute)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_up_slice_status_update(self, ap_slice_id, ap_name, success=False):
        """Invoked upon receipt of a message from an active
        access point.  Modifies slice status depending on
        whether the associated command was successful.

        :param str ap_slice_id:
        :param str ap_name:
        :param bool success:

        """
        now = datetime.datetime.now()
        try:
            with self._database_connection() as db:
                if success:
                    to_execute = ("""UPDATE metering, ap_slice SET 
                                         metering.last_time_activated=
                                             CASE ap_slice.status
                                                 WHEN 'PENDING' THEN '%s'
                                                 WHEN 'DOWN' THEN '%s'
                                             ELSE metering.last_time_activated END,
                                         metering.current_mb_sent=
                                             CASE ap_slice.status
                                                 WHEN 'PENDING' THEN 0
                                                 WHEN 'DOWN' THEN 0
                                             ELSE metering.current_mb_sent END,
                                         metering.last_time_updated=
                                             NULL
                                         WHERE 
                                             metering.ap_slice_id='%s' AND
                                             ap_slice.physical_ap='%s'""" %
                                     (now, now, ap_slice_id, ap_name)
                                 )
                    self.LOGGER.debug(to_execute)
                    db.execute(to_execute)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

        try:
            with self._database_connection() as db:
                if success:
                    to_execute = ("""UPDATE ap_slice SET
                                         status= 
                                             CASE status 
                                                 WHEN 'PENDING' THEN 'ACTIVE' 
                                                 WHEN 'DELETING' THEN 'DELETED' 
                                                 WHEN 'DOWN' THEN 'ACTIVE' 
                                             ELSE status END
                                         WHERE 
                                             ap_slice_id='%s' AND
                                             physical_ap='%s'""" %
                                     (ap_slice_id, ap_name)
                                 )
                else:
                    to_execute = ("""UPDATE ap_slice SET 
                                         status='FAILED' 
                                         WHERE ap_slice_id='%s'""" % ap_slice_id
                                 )
                self.LOGGER.debug(to_execute)
                db.execute(to_execute)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def ap_down_slice_status_update(self, ap_name=None, ap_slice_id=None):
        """Invoked upon non-receipt timeout of a message, or by 
        an access point sending a FIN message.  Marks all slices
        associated with the AP appropriately depending on their 
        current status, notably active slices are marked 'DOWN'.

        :param str ap_slice_id:
        :param str ap_name:

        """
        try:
            with self._database_connection() as db:
                to_execute = ("""UPDATE ap_slice SET 
                                     status=
                                         CASE status 
                                             WHEN 'ACTIVE' THEN 'DOWN'
                                             WHEN 'DELETING' THEN 'DELETED'
                                             WHEN 'PENDING' THEN 'FAILED'
                                         ELSE status END
                                     WHERE physical_ap='%s'""" % ap_name
                             )
                self.LOGGER.debug(to_execute)
                db.execute(to_execute)
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)

    def wslice_belongs_to(self, tenant_id, project_id, ap_slice_id):
        """Method to check the ownership of a slice.  Returns true if
        the given slice ID is owned by the tenant in question, and is
        attributed to the same project.

        :param int tenant_id:
        :param int project_id:
        :param str ap_slice_id:
        :rtype: bool

        """
        if tenant_id == 0:
            return True
        else:
            try:
                with self._database_connection() as db:
                    to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                                   "tenant_id = '%s' AND "
                                   "project_id = '%s'" % (tenant_id, project_id) )
                    db.execute(to_execute)
                    tenant_ap_slices_tt = db.fetchall()
                    tenant_ap_slices = []
                    for tenant_t in tenant_ap_slices_tt:
                        tenant_ap_slices.append(tenant_t[0])
                    if ap_slice_id in tenant_ap_slices:
                        return True

            except mdb.Error as e:
                traceback.print_exc(file=sys.stdout)
        return False

    def wnet_belongs_to(self, tenant_id, project_id, wnet_name):
        """Method to check the ownership of a wnet.  Returns true if
        the given wnet name is owned by the tenant in question, and is
        attributed to the same project.

        :param int tenant_id:
        :param int project_id:
        :param str wnet_name:
        :rtype: bool

        """
        if tenant_id == 0:
            return True
        else:
            try:
                with self._database_connection() as db:
                    to_execute = ( "SELECT name, wnet_id FROM wnet WHERE "
                                   "tenant_id = '%s' AND "
                                   "project_id = '%s'" % (tenant_id, project_id) )
                    db.execute(to_execute)
                    tenant_wnets_tt = db.fetchall()

                    tenant_wnets = []
                    for t in tenant_wnets_tt:
                        tenant_wnets.append(t[0])
                        tenant_wnets.append(t[1])
                    if wnet_name in tenant_wnets:
                        return True
            except mdb.Error as e:
                    traceback.print_exc(file=sys.stdout)
        return False

    def wslice_is_deleted(self, ap_slice_id):
        """Method which determines whether a slice is deleted.

        :param str ap_slice_id:
        :rtype: bool

        """
        try:
           with self._database_connection() as db:
                to_execute = ( "SELECT status FROM ap_slice WHERE "
                               "ap_slice_id = '%s'" % (ap_slice_id) )
                db.execute(to_execute)
                status = db.fetchone()
                if (status[0] == 'DELETED' or
                    status[0] == 'DELETING'):
                    return True
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)
        return False

    def wslice_has_tag(self, ap_slice_id, tag):
        """Determines whether a specific slice is marked 
        with the given tag.

        :param str ap_slice_id:
        :param str tag:
        :rtype: bool

        """
        try:
            with self._database_connection() as db:
                to_execute = ( "SELECT name FROM tenant_tags WHERE "
                               "ap_slice_id = '%s'" % ap_slice_id )
                db.execute(to_execute)
                ap_slice_tags_tt = db.fetchall()
                ap_slice_tags = []
                for tag_t in ap_slice_tags_tt:
                    ap_slice_tags.append(tag_t[0])
                if tag in ap_slice_tags:
                    return True
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)
        return False

    def wnet_add_wslice(self, tenant_id, slice_id, name):
        """Adds an ap slice to a wnet.  Both slice and wnet 

        :param int tenant_id:
        :param str slice_id:
        :param str name:
        :returns: str - Message for client
        :raises: NoWnetExistsForTenantException, APSliceAlreadyInWnetException

        """
        try:
            with self._database_connection() as db:
                # First get wnet-id
                # TODO(mk): Catch tenant 0 call, ambiguous with multiple 
                # wnets of same name
                to_execute = (
                    """SELECT wnet_id FROM 
                               wnet 
                           WHERE 
                               wnet_id='%s' AND tenant_id = '%s' OR 
                               name='%s' AND tenant_id = '%s'""" % 
                       (name, tenant_id, name, tenant_id)
                )
                num_results = db.execute(to_execute)
                if num_results < 1:
                    raise NoWnetExistsForTenantException(wnet=name)

                wnetID = db.fetchone()[0]
                to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                               "wnet_id = '%s'" % wnetID )
                db.execute(to_execute)
                ap_slice_id_tt = db.fetchall()
                ap_slice_id = []
                for id_t in ap_slice_id_tt:
                    ap_slice_id.append(id_t[0])
                if slice_id in ap_slice_id:
                    raise APSliceAlreadyInWnetException(ap_slice_id=slice_id, 
                                                        wnet=name)
                else:
                    #Update to SQL database
                    to_execute = ( "UPDATE ap_slice SET wnet_id='%s' WHERE "
                                   "ap_slice_id='%s'" % (wnetID, slice_id) )
                    db.execute(to_execute)
                    return "Added '%s' to '%s'.\n" % (slice_id, name)

        except mdb.Error as e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            self.LOGGER.error(err_msg)
            return err_msg + '\n'

    def wnet_remove_wslice(self, tenant_id, slice_id, name):
        #Update to SQL database
        try:
            with self._database_connection() as db:
                #First get wnet-id

                try:
                    wnet_info = self.get_wnet_name_id(name, tenant_id)
                except Exception as e:
                    raise Exception(e.message)

                wnet_id = wnet_info['wnet_id']
                wnet_name = wnet_info['name']


                #Update to SQL database
                to_execute = ( "UPDATE ap_slice SET wnet_id=NULL WHERE "
                               "ap_slice_id='%s' AND "
                               "wnet_id='%s' AND tenant_id = '%s'" % (slice_id, wnet_id, tenant_id) )
                db.execute(to_execute)
                return "%s: %s removed\n" % (wnet_name, slice_id)
                #TODO: Add messaging
        except mdb.Error as e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            self.LOGGER.error(err_msg)
            return err_msg + '\n'

    def wnet_add(self, wnet_id, name, tenant_id, project_id):
        #Update the SQL database
        try:
            with self._database_connection() as db:
                to_execute = ( "SELECT wnet_id FROM wnet WHERE "
                               "name = '%s' AND tenant_id = '%s'" % (name, tenant_id) )
                db.execute(to_execute)
                wnet_id_tt = db.fetchall()
                if len(wnet_id_tt) > 0:
                    return "You already own '%s'.\n" % name
                else:

                    to_execute = ( "INSERT INTO wnet VALUES ('%s', '%s', %s, %s)" %
                                   (wnet_id, name, tenant_id, project_id) )
                    db.execute(to_execute)
                    return "Created '%s'.\n" % name
        except mdb.Error as e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            self.LOGGER.error(err_msg)
            return err_msg + '\n'

    def wnet_remove(self, wnet_arg, tenant_id):
        #Update the SQL database, at this point we know the wnet exists under the specified tenant
        #TODO: remove association from ap_slices
        try:
            with self._database_connection() as db:
                message = ""
                try:
                    wnet_info = self.get_wnet_name_id(wnet_arg, tenant_id)
                except Exception as e:
                    raise Exception(e.message)
                wnet_id = wnet_info['wnet_id']
                wnet_name = wnet_info['name']

                if tenant_id == 0:
                    to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                                   "wnet_id = '%s'" % wnet_id )
           #         to_execute_slice = ( "UPDATE ap_slice SET wnet_id = NULL WHERE "
           #                              "wnet_id = '%s'" % wnet_id )
                    to_execute_wnet = ( "DELETE FROM wnet WHERE wnet_id = '%s'" % wnet_id )
                else:
                    to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                                   "wnet_id = '%s' AND tenant_id = '%s'" %
                                   (wnet_id, tenant_id) )
           #         to_execute_slice = ( "UPDATE ap_slice SET wnet_id = NULL WHERE "
           #                            "wnet_id = '%s' AND tenant_id = '%s'" %
           #                            (wnet_id, tenant_id) )
                    to_execute_wnet = ( "DELETE FROM wnet WHERE wnet_id = '%s'"
                                        "AND tenant_id = '%s'" % (wnet_id, tenant_id) )
                db.execute(to_execute)
                slice_id_tt = db.fetchall()
                if slice_id_tt:
             #       message += "\nRemoving slices from '%s':" % wnet_arg
                    for slice_id_t in slice_id_tt:
                        message += self.wnet_remove_wslice(tenant_id, slice_id_t[0], wnet_id)
                    message += '\n'
           #     db.execute(to_execute_slice)
                message += "Deleting '%s'.\n" % wnet_arg
                db.execute(to_execute_wnet)

        except mdb.Error as e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            self.LOGGER.error(err_msg)
            return err_msg + '\n'
        return message

    def wslice_add(self, slice_uuid, slice_ssid, tenant_id, physAP, project_id):
        try:
            with self._database_connection() as db:
                to_execute = ( "INSERT INTO ap_slice VALUES ('%s', '%s', %s, '%s', %s, %s, '%s')" %
                               (slice_uuid, slice_ssid, tenant_id, physAP,
                                project_id, "NULL", "PENDING")
                             )
                db.execute(to_execute)
                to_execute = ( "INSERT INTO metering SET ap_slice_id='%s'" % slice_uuid)
                db.execute(to_execute)
                #return "Adding slice %s on %s.\n" % (slice_uuid, physAP)
                return None
                #We the manager calling this method will generate this message after calling.
                #Therefore it is not necessary to return a success notification. The message
                #can be used for testing purposes.
                #Return None when there is no problem instead.
        except mdb.Error as e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            self.LOGGER.error(err_msg)
            return err_msg + '\n'

    def wslice_delete(self, slice_id):
        #Update SQL database and JSON file
        #Remove tags
        try:
            with self._database_connection() as db:
                to_execute = ( "UPDATE ap_slice SET status='DELETING' WHERE "
                               "ap_slice_id='%s'" % slice_id )
                db.execute(to_execute)
                to_execute = ( "DELETE FROM tenant_tags WHERE "
                               "ap_slice_id='%s'" % slice_id )
                db.execute(to_execute)
                return "Deleting slice %s.\n" % slice_id
        except mdb.Error as e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            self.LOGGER.error(err_msg)
            return err_msg + '\n'

    def wslice_add_tag(self, ap_slice_id, tag):
        if self.wslice_has_tag(ap_slice_id, tag):
            return "Tag '%s' already exists for ap_slice '%s'\n" % (tag, ap_slice_id)
        else:
            try:
                with self._database_connection() as db:
                    to_execute = "INSERT INTO tenant_tags VALUES (%s, '%s')" % (tag, ap_slice_id)
                    db.execute(to_execute)
                    return "Added tag '%s' to ap_slice '%s'.\n" % (tag, ap_slice_id)
            except mdb.Error as e:
                err_msg = "Error %d: %s\n" % (e.args[0], e.args[1])
                self.LOGGER.error(err_msg)
                return err_msg + '\n'

    def wslice_remove_tag(self, ap_slice_id, tag):
        if self.wslice_has_tag(ap_slice_id, tag):
            try:
                with self._database_connection() as db:
                    to_execute = ( "DELETE FROM tenant_tags WHERE "
                                   "name='%s' AND ap_slice_id='%s'" %
                                   (tag, ap_slice_id) )
                    db.execute(to_execute)
                    return "Deleted tag '%s' from ap_slice '%s'\n" % (tag, ap_slice_id)
            except mdb.Error as e:
                err_msg = "Error %d: %s\n" % (e.args[0], e.args[1])
                self.LOGGER.error(err_msg)
                return err_msg + '\n'
        else:
            return "Tag '%s' not found.\n" % (tag)

    def wnet_join(self, tenant_id, name):
        pass #TODO AFTER SAVI INTEGRATION

    def get_ap_list(self):
        try:
            with self._database_connection() as db:
                db.execute("SELECT name FROM ap")
                ap_list = []
                for ap_tuple in db.fetchall():
                    ap_list.append(ap_tuple[0])
                return ap_list
        except mdb.Error as e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)

    def get_user_for_active_ap_slice(self, ap_slice_id):
        try:
            with self._database_connection() as db:
                to_execute = ("""SELECT tenant_id 
                                 FROM ap_slice 
                                 WHERE 
                                     ap_slice_id='%s' AND 
                                     status<>'DELETED' AND 
                                     status<>'DELETING'""" % ap_slice_id)
                self.LOGGER.debug(to_execute)
                num_lines = db.execute(to_execute)
                if num_lines > 0:
                    return int(db.fetchone()[0])
        except mdb.Error as e:
            traceback.print_exc(file=sys.stdout)
        return

    def get_wslice_physical_ap(self, ap_slice_id):
        try:
            with self._database_connection() as db:
                to_execute = ( "SELECT physical_ap FROM ap_slice WHERE "
                               "ap_slice_id='%s'" % ap_slice_id )
                db.execute(to_execute)
                physical_ap = db.fetchone()
                if physical_ap:
                    return physical_ap[0]
                else:
                    raise Exception("No slice '%s'\n" % ap_slice_id)
        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)

    def get_physical_ap_slices(self, ap_name):
        try:
            with self._database_connection() as db:
                to_execute = ("""SELECT ap_slice_id
                                     FROM ap_slice
                                     WHERE physical_ap='%s'""" %
                                 (ap_name)
                             )
                db.execute(to_execute)
                result = db.fetchall()
                slice_list = []
                for ap_slice_id in result:
                    slice_list.append(ap_slice_id[0])
                return slice_list
        except mdb.Error as e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)

    def get_wnet_list(self, tenant_id, wnet_arg = None):
        try:
            with self._database_connection() as db:
                if tenant_id == 0:
                    to_execute = "SELECT * FROM wnet"
                elif wnet_arg:
                    to_execute = ( "SELECT * FROM wnet WHERE "
                                   "tenant_id = '%s' AND wnet_id = '%s' OR "
                                   "tenant_id = '%s' AND name = '%s'" %
                                   (tenant_id, wnet_arg, tenant_id, wnet_arg) )
                else:
                    to_execute = "SELECT * FROM wnet WHERE tenant_id = '%s'" % tenant_id
                db.execute(to_execute)
                wnet_tt = db.fetchall()
                if not wnet_tt:
                    err_msg = "AuroraDB Error: No wnets available"
                    if wnet_arg:
                        err_msg += " by handle '%s'" % wnet_arg
                    err_msg += ".\n"
                    raise Exception(err_msg)
                #Prune through list
                wnet_list = []
                for (i, wnet_t) in enumerate(wnet_tt):
                    wnet_list.append({})
                    wnet_list[i]['wnet_id'] = wnet_t[0]
                    wnet_list[i]['name'] = wnet_t[1]
                    wnet_list[i]['tenant_id'] = wnet_t[2]
                    wnet_list[i]['project_id'] = wnet_t[3]
        except mdb.Error as e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)
        return wnet_list

    def get_wnet_slices(self, wnet_arg, tenant_id):
        try:
            with self._database_connection() as db:
                wnet_id = self.get_wnet_name_id(wnet_arg, tenant_id)['wnet_id']

                #Get slices associated with this wnet
                db.execute( "SELECT * FROM ap_slice WHERE "
                             "wnet_id = '%s'" % wnet_id )
                slice_info_tt = db.fetchall()

                #Prune through list
                slice_list = []
                for (i, slice_t) in enumerate(slice_info_tt):
                    slice_list.append({})
                    slice_list[i]['ap_slice_id'] = slice_t[0]
                    slice_list[i]['ap_slice_ssid'] = slice_t[1]
                    slice_list[i]['tenant_id'] = slice_t[2]
                    slice_list[i]['physical_ap'] = slice_t[3]
                    slice_list[i]['project_id'] = slice_t[4]
                    slice_list[i]['wnet_id'] = slice_t[5]
                    slice_list[i]['status'] = slice_t[6]
        except mdb.Error as e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)
        return slice_list

    def get_wnet_name_id(self, wnet_arg, tenant_id):
        try:
            with self._database_connection() as db:
                wnet_info = {}
                if tenant_id == 0:
                    to_execute = ( "SELECT wnet_id, name FROM wnet WHERE "
                                   "name='%s' OR wnet_id = '%s'" % (wnet_arg, wnet_arg) )
                else:
                    to_execute = ( "SELECT wnet_id, name FROM wnet WHERE "
                                   "name='%s' AND tenant_id = '%s' OR "
                                   "wnet_id='%s' AND tenant_id = '%s'" %
                                   (wnet_arg, tenant_id, wnet_arg, tenant_id) )
                db.execute(to_execute)
                wnet_info_tt = db.fetchall()
                if not wnet_info_tt:
                    raise Exception("AuroraDB Error: No wnet '%s'.\n" % wnet_arg)
                elif tenant_id == 0 and len(wnet_info_tt) > 1:
                    err_msg = "Ambiguous input.  Did you mean:"
                    for wnet_info_t in wnet_info_tt:
                        err_msg += "\n\t%s: %s - %s" % (wnet_arg, wnet_info_t[0], wnet_info-t[1])
                    raise Exception(err_msg)
                else:
                    wnet_info['wnet_id'] = wnet_info_tt[0][0]
                    wnet_info['name'] = wnet_info_tt[0][1]

        except mdb.Error as e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)
        return wnet_info


