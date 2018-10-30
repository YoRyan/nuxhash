#!/bin/sh

VERSION='1.5.13a'
SHA256='997f585216e9368efb846b03db2ae7612984beea303c3740caf5a4b32af60319'

case "$1" in
verify)
        [ -f excavator ] && [ `sha256sum excavator | awk '{print $1}'` = "$SHA256" ]
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

