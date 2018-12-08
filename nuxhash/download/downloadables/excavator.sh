#!/bin/sh

VERSION='1.5.14a'
SHA256='e814107a5c1df119b4f7c40c36c53e8324688508da10543f2ad94c5368c43225'

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

