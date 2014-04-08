#!/bin/bash

# Need root to run
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

EXTIF=${2:-"eth0"}
INTIF=${3:-"brint"}

uninstall() {
    /etc/init.d/auto_capsulator stop
    rm /etc/init.d/auto_capsulator
    rm /usr/local/bin/auto_capsulator
    chmod +x rc.default-iptables
    ./rc.default-iptables
    iptables-save

    ifconfig $INTIF 0 down
    brctl delbr $INTIF
    rm /usr/local/bin/capsulator
    rm -r Capsulator
    rm /usr/bin/gmake
    return 0
}

install() {

    uninstall

    # Get required packages using apt-get
    apt-get update
    apt-get upgrade -y
    apt-get install -y dnsmasq bridge-utils git make build-essential python-dev \
    iptables-persistent

    # Install capsulator
    git clone git://github.com/peymank/Capsulator.git
    ln -s /usr/bin/make /usr/bin/gmake
    cd Capsulator
    make
    ln -s $PWD/capsulator /usr/local/bin/capsulator
    cd ..

    # Create a bridge to which capsulator interfaces can be attached
    brctl addbr $INTIF
    ifconfig $INTIF up 192.168.0.1/24
    echo "interface=$INTIF" >> /etc/dnsmasq.conf
    echo "dhcp-range=192.168.0.50,192.168.0.150,12h" >> /etc/dnsmasq.conf
    /etc/init.d/dnsmasq restart

    # Masquerade all traffic arriving on the internal bridge, sending
    chmod +x rc.firewall-iptables rc.default-iptables

    # Verify $EXTIF exists
    ifconfig $EXTIF >/dev/null || return 1

    ./rc.firewall-iptables $EXTIF $INTIF
    iptables-save

    chmod +x auto_capsulator.py auto_capsulator.d
    cp auto_capsulator.py /usr/local/bin/auto_capsulator
    cp auto_capsulator.d /etc/init.d/auto_capsulator
    /etc/init.d/auto_capsulator start $INTIF
    return 0
}



case $1 in
    install)
        install || exit 1
    ;;
    uninstall)
        uninstall || exit 1
    ;;
    *)
        echo "Usage: setup.sh (install|uninstall) [EXTIF] [INTIF]"
        exit 1
    ;;
esac
exit 0