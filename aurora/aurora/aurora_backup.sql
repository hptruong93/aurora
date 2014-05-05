-- MySQL dump 10.13  Distrib 5.5.34, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: aurora
-- ------------------------------------------------------
-- Server version	5.5.34-0ubuntu0.12.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ap`
--

DROP TABLE IF EXISTS `ap`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ap` (
  `name` varchar(255) NOT NULL,
  `region` varchar(255) DEFAULT NULL,
  `firmware` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `number_radio` int(11) DEFAULT NULL,
  `memory_mb` int(11) DEFAULT NULL,
  `free_disk` int(11) DEFAULT NULL,
  `supported_protocol` varchar(255) DEFAULT 'a/b/g',
  `number_radio_free` int(11) DEFAULT NULL,
  `number_slice_free` int(11) DEFAULT NULL,
  `status` enum('UP','DOWN','UNKNOWN') DEFAULT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ap_slice`
--

DROP TABLE IF EXISTS `ap_slice`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ap_slice` (
  `ap_slice_id` varchar(40) NOT NULL,
  `ap_slice_ssid` varchar(255) DEFAULT NULL,
  `tenant_id` varchar(255) DEFAULT NULL,
  `physical_ap` varchar(255) DEFAULT NULL,
  `project_id` varchar(255) DEFAULT NULL,
  `wnet_id` varchar(40) DEFAULT NULL,
  `status` enum('PENDING','ACTIVE','FAILED','DOWN','DELETING','DELETED') DEFAULT NULL,
  PRIMARY KEY (`ap_slice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `location_tags`
--

DROP TABLE IF EXISTS `location_tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `location_tags` (
  `name` varchar(255) NOT NULL DEFAULT '',
  `ap_name` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`name`,`ap_name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `metering`
--

DROP TABLE IF EXISTS `metering`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `metering` (
  `ap_slice_id` varchar(40) NOT NULL,
  `current_mb_sent` float DEFAULT '0',
  `total_mb_sent` float DEFAULT '0',
  `current_active_duration` time DEFAULT '00:00:00',
  `total_active_duration` time DEFAULT '00:00:00',
  `last_time_activated` datetime DEFAULT NULL,
  `last_time_updated` datetime DEFAULT NULL,
  PRIMARY KEY (`ap_slice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenant_tags`
--

DROP TABLE IF EXISTS `tenant_tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenant_tags` (
  `name` varchar(255) NOT NULL DEFAULT '',
  `ap_slice_id` varchar(40) NOT NULL DEFAULT '',
  PRIMARY KEY (`name`,`ap_slice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wnet`
--

DROP TABLE IF EXISTS `wnet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wnet` (
  `wnet_id` varchar(40) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `tenant_id` varchar(255) DEFAULT NULL,
  `project_id` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`wnet_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2014-05-02 14:53:42
