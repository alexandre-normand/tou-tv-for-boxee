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

# IMPORTANT: Remove this once the boxee team fixes their bugs that affect the boxee box versions. This restricts the app to non boxee box versions. 
sed -i.bak 's/\<minversion\>0\.9\.11\<\/minversion\>/\<minversion\>0\.9\.11\<\/minversion\>\
  \<maxversion\>0\.9\.29\<\/maxversion\>/g' descriptor.xml
rm descriptor.xml.bak

# Zip files
zip -r ../../releases/tou-tv-$VERSION.zip -xi .

cd ../..
rm -rf packaging_release

exit 0