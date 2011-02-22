#!/bin/bash -x

VERSION=`cat com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml | grep "<version>" | sed -e 's/ //g' -e 's/<version>//' -e 's/<\/version>//'`

# Delete previous version
rm -f releases/tou-tv-$VERSION.zip

# Create packaging folder
mkdir packaging_release
cd packaging_release

#Export files in folder
svn export ../com.googlecode.tou-tv-for-boxee.tou-tv tou-tv

cd tou-tv

# Zip files
zip -r ../../releases/tou-tv-$VERSION.zip -xi .

cd ../..
rm -rf packaging_release

exit 0