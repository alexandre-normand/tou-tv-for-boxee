#!/bin/bash
rm -rf ~/.boxee/UserData/apps/*tou-tv*
cp -Rf com.googlecode.tou-tv-for-boxee.tou-tv ~/.boxee/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv

#Add repository tag for signing for custom repository
sed -i.bak 's/tv.boxee/com.googlecode.tou-tv-for-boxee/g' ~/.boxee/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml

#Replace id for custom repository
sed -i.bak 's/tou-tv/com.googlecode.tou-tv-for-boxee.tou-tv/g' ~/.boxee/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml
