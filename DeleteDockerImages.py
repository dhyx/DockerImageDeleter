#Author: John Blood
#Created Date: 1/25/2018

#Do Not Forget to turn on delete on the production server!
#storage:
#  delete:
#    enabled: true

#This script requires python 3.0 or higher and pip with the requests package installed
#python -m ensurepip --default-pip
#python -m pip install --upgrade requests

import requests
import json
import re
import argparse


#https://docs.python.org/3.4/library/argparse.html
parser = argparse.ArgumentParser(prog='Docker Deleter', description='Delete Docker Images from Private Repository')

parser.add_argument('-s', help='Server Name', required=True, dest='serverName')
parser.add_argument('-u', help='User Name',required=True, dest='userName')
parser.add_argument('-p', help='Password', required=True, dest='password')
parser.add_argument('-c', help='Configuration File', dest='config')
parser.add_argument('-a', help='Applications to delete from', dest='apps', nargs='+')
parser.add_argument('-v', help='Versions to delete', dest='versions', nargs='+')

args = parser.parse_args()

serverName = args.serverName
userName = args.userName
password = args.password
config = args.config
applications = args.apps
versions = args.versions

if(applications == None):
	versions = None
	#Get All Repositories in Catalog
	catalogList = requests.get('https://{0}/v2/_catalog'.format(serverName),auth=(userName,password))
	print(catalogList.text)
	parseCatalog = json.loads(catalogList.text)
	applications = parseCatalog["repositories"]
elif(len(applications) > 1):
	versions == None

#Read Config File
with open(config,"r") as configFile:
	#print(configFile.read())
	configData = json.load(configFile)
configFile.close()
print(configData["images"])


	
#Create Regex to find all non-numeric or period characters
non_decimal = re.compile(r'[^\d.]+')

#loop through each repository in the catalog
for application in applications:
	
	if( application in configData["images"]):
		numberToKeep = configData["images"][application]
	else:
		numberToKeep = configData["default"]
	 
	print("{0}, keeping up to {1}".format(application,numberToKeep))
	 
	if(versions == None):
		# for each application get versions
		tagList = requests.get('https://{0}/v2/{1}/tags/list'.format(serverName,application),auth=(userName,password))
		versions = json.loads(tagList.text)["tags"]
	
	#Clean each tag and append to clean list. Element 0 is the clean tag version, element 1 is the actual tag name
	cleanList = list()

	for x in versions:
		versionSort = non_decimal.sub('',x)
		cleanList.append([versionSort,x])
		
	hasNumericVersion = cleanList[0][0] != ''
	if len(cleanList) > 0:
		
		if(hasNumericVersion):
			cleanList.sort(key=lambda s: list(map(int, s[0].split('.'))))	

		#Bounds checking, if asking to keep more than we have, keep all
		if numberToKeep > len(cleanList):
			numberToKeep = len(cleanList)

		#Get List of Tags to Delete
		numberToDelete = len(cleanList) - numberToKeep
		
		#Bounds checking if numberToDelete < 0, delete none
		if(numberToDelete < 0):
			numberToDelete = 0
		
		delete = cleanList[:numberToDelete]

		#Sort Reverse and get Tags to Keep
		if(hasNumericVersion):
			cleanList.sort(key=lambda s: list(map(int, s[0].split('.'))),reverse=True)
		keep = cleanList[:numberToKeep]
		print("\tDeleting {0} images and keeping {1} images".format(numberToDelete,numberToKeep))
		
		
		if(len(delete) > 0):
			#Perform Delete Actions
			for deleteable in delete:
				tag = deleteable[1]
				manifest = requests.get('https://{0}/v2/{1}/manifests/{2}'.format(serverName,application,tag),auth=(userName,password),headers={'Accept': 'application/vnd.docker.distribution.manifest.v2+json'})
				imageDigest = manifest.headers["docker-content-digest"] 
				
				print("\tDeleting {0} - {1}".format(tag,imageDigest))
				reqDeleteImage = requests.delete('https://{0}/v2/{1}/manifests/{2}'.format(serverName,application,imageDigest),auth=(userName,password),headers={'Accept': 'application/vnd.docker.distribution.manifest.v2+json'})
				
				if(reqDeleteImage.status_code == 202):
					print("success\n")
				else:
					print("fail: code {0}\n".format(reqDeleteImage.status_code))
		else:
			print("\tNo images to delete for: {0}\n".format(application))