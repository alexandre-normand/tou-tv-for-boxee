#!/bin/sh
cd /Volumes/Bubble/projects/tou-tv-for-boxee
rm -r ~/Library/Application\ Support/BOXEE/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv
svn export com.googlecode.tou-tv-for-boxee.tou-tv ~/Library/Application\ Support/BOXEE/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv
cp com.googlecode.tou-tv-for-boxee.tou-tv/skin/Boxee\ Skin\ NG/media/*.png ~/Library/Application\ Support/BOXEE/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv/skin/Boxee\ Skin\ NG/media/

sed -i.bak 's/<\/app>/<test-app>true<\/test-app><\/app>/g' ~/Library/Application\ Support/BOXEE/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml

#Replace id for custom repository
sed -i.bak 's/\<id\>tou-tv\<\/id\>/\<id\>com.googlecode.tou-tv-for-boxee.tou-tv\<\/id\>/g' ~/Library/Application\ Support/BOXEE/UserData/apps/com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml
