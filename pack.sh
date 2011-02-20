#!/bin/bash -x

VERSION=`cat com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml | grep "<version>" | sed -e 's/ //g' -e 's/<version>//' -e 's/<\/version>//'`

# Delete previous version
rm -f boxee/download/com.googlecode.tou-tv-for-boxee.tou-tv-$VERSION.zip

# Create packaging folder
mkdir packaging
cd packaging

#Export files in folder
svn export ../com.googlecode.tou-tv-for-boxee.tou-tv com.googlecode.tou-tv-for-boxee.tou-tv

#Add repository tag for signing for custom repository
sed -i.bak 's/<\/app>/<repository>com.googlecode.tou-tv-for-boxee<\/repository><\/app>/g' com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml

# Zip files
zip -r ../boxee/download/com.googlecode.tou-tv-for-boxee.tou-tv-$VERSION.zip -xi .

cd -
rm -rf packaging

exit 0