#!/bin/sh

VERSION='1.5.5a'
MD5='270b14d9a177397b58f5e6696021ed4d'

case "$1" in
verify)
        [ -f excavator ] && [ `md5sum excavator | awk '{print $1}'` = "$MD5" ]
        exit $?
        ;;
download)
        curl -L -O "https://github.com/nicehash/excavator/releases/download/v${VERSION}/excavator_${VERSION}_amd64.deb"
        ar x "excavator_${VERSION}_amd64.deb" data.tar.xz
        tar xf data.tar.xz --strip-components 4 ./opt/excavator/bin/excavator
        rm -f "excavator_${VERSION}_amd64.deb" data.tar.xz
        exit 0
        ;;
esac

