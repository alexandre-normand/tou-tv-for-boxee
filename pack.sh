#!/bin/bash

VERSION=`cat com.googlecode.tou-tv-for-boxee.tou-tv/descriptor.xml | grep "<version>" | sed -e 's/ //g' -e 's/<version>//' -e 's/<\/version>//'`

mkdir packaging
cd packaging

svn export ../com.googlecode.tou-tv-for-boxee.tou-tv com.googlecode.tou-tv-for-boxee.tou-tv

zip -r ../boxee/download/com.googlecode.tou-tv-for-boxee.tou-tv-$VERSION.zip -xi com.googlecode.tou-tv-for-boxee.tou-tv

cd -
rm -rf packaging