import Fs
import Fs.Pfs0
import Fs.Nca
import Fs.Type
import os
import glob
import re
from nut import Print


def ExtractHashes(gamePath):
	fileHashes = set()
	gamePath = os.path.abspath(gamePath)
	container = Fs.factory(gamePath)
	container.open(gamePath, 'rb')
	try:
		for nspf in container:
			if isinstance(nspf, Fs.Nca.Nca) and nspf.header.contentType == Fs.Type.Content.META:
				for section in nspf:
					if isinstance(section, Fs.Pfs0.Pfs0):
						Cnmt = section.getCnmt()
						for entry in Cnmt.contentEntries:
							fileHashes.add(entry.hash.hex())
	finally:
		container.close()
	
	return fileHashes


def ExtractTitleIDAndVersion(gamePath):
	titleId = ""
	version = -1
	
	#If filename includes titleID this will speed up skipping existing files immensely.
	gameName = os.path.basename(gamePath)
	titleIdResult = re.search(r'0100[0-9A-Fa-f]{12}', gameName)
	if titleIdResult:
		titleId = titleIdResult.group()
		
	versionResult = re.search(r'\[v\d+\]', gameName)
	if versionResult:
		version = int(versionResult.group()[2:-1])
	
	if titleId != "" and version > -1 and version%65536 == 0:
		return(titleId, version)
	
	gamePath = os.path.abspath(gamePath)
	container = Fs.factory(gamePath)
	container.open(gamePath, 'rb')
	try:
		for nspf in container:
			if isinstance(nspf, Fs.Nca.Nca) and nspf.header.contentType == Fs.Type.Content.META:
				for section in nspf:
					if isinstance(section, Fs.Pfs0.Pfs0):
						Cnmt = section.getCnmt()
						titleId = Cnmt.titleId
						version = Cnmt.version
	finally:
		container.close()
	
	if titleId != "" and version > -1 and version%65536 == 0:
		return(titleId, version)
		
	raise("Failed to determinate TitleID/Version!")


def CreateTargetDict(targetFolder, extension):
	filesAtTarget = set()
	alreadyExists = {}
	for file in os.scandir(targetFolder):
		filePath = os.path.join(targetFolder, file)
		if file.name.endswith(extension):
			Print.infoNoNewline('Extract TitleID/Version: {0} '.format(file.name))
			filesAtTarget.add(file.name.lower())
			(titleID, version) = ExtractTitleIDAndVersion(file)
			titleIDEntry = alreadyExists.get(titleID)
			if titleIDEntry == None:
				titleIDEntry = {version: {filePath}}
			elif not version in titleIDEntry:
				titleIDEntry.add({version: {filePath}})
			else:
				titleIDEntry[version].add(filePath)
			alreadyExists[titleID] = titleIDEntry
			Print.info('=> {0} {1}'.format(titleID, version))
	return(filesAtTarget, alreadyExists)


def AllowedToWriteOutfile(filePath, targetFileExtension, targetDict, removeOld, overwrite):
	(titleID, version) = ExtractTitleIDAndVersion(filePath)
	(filesAtTarget, alreadyExists) = targetDict
	
	if removeOld:
		titleIDEntry = alreadyExists.get(titleID)
		if not titleIDEntry == None:
			exitFlag = False
			for versionEntry in titleIDEntry:
				if versionEntry < titleIDEntry:
					for filePath in fileList:
						Print.info('Delete outdated version: {0}'.format(filePath))
						fileList.remove(filePath)
						filesAtTarget.remove(os.path.basename(filePath).name.lower())
						#os.remove(file)
				else:
					exitFlag = True
			if exitFlag:
				Print.info('{0} with a the same ID and newer version already exists in the output directory.\n'\
				'If you want to process it do not use --rm-old-version!'.format(filePath))
				return False
	
	titleIDEntry = alreadyExists.get(titleID)
	if not titleIDEntry == None:
		for versionEntry in titleIDEntry:
			if versionEntry == titleIDEntry:
				if overwrite:
					for filePath in fileList:
						Print.info('Delete dublicate: {0}'.format(filePath))
						fileList.remove(filePath)
						filesAtTarget.remove(os.path.basename(filePath).name.lower())
						#os.remove(file)
				else:
					Print.info('{0} with the same ID and version already exists in the output directory.\n'\
					'If you want to overwrite it use the -w parameter!'.format(filePath))
					return False
	
	
	outFile = (os.path.splitext(os.path.basename(filePath))[0]+targetFileExtension).lower()
	if not overwrite and outFile in filesAtTarget:
		Print.info('{0} with the same file name already exists in the output directory.\n'\
		'If you want to overwrite it use the -w parameter!'.format(filePath))
		return False
	
	return True
