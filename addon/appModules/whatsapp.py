# -*- coding: utf-8 -*-
# Copyright (C) 2021 Gerardo Kessler <ReaperYOtrasYerbas@gmail.com>
# This file is covered by the GNU General Public License.
# Canal de actualización y creación de ventanas por Héctor J. Benítez Corredera <xebolax@gmail.com>

from globalVars import appArgs
import appModuleHandler
from scriptHandler import script
import api
from ui import message
from nvwave import playWaveFile
from re import search, sub
import os
import addonHandler

# Lína de traducción
addonHandler.initTranslation()

class AppModule(appModuleHandler.AppModule):

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		self.switch = None
		self.globalObject = None
		self.lastChat = None
		self.soundsPath = os.path.join(appArgs.configPath, "addons", "WhatsApp-desktop", "appModules", "sounds")
		self.configFile()

	def configFile(self):
		try:
			with open(f"{appArgs.configPath}\\whatsapp.ini", "r") as f:
				self.viewConfig = f.read()
		except FileNotFoundError:
			with open(f"{appArgs.configPath}\\whatsapp.ini", "w") as f:
				f.write("desactivado")

	def event_NVDAObject_init(self, obj):
		try:
			if obj.UIAAutomationId == 'RightButton' and obj.previous.description == '':
				obj.name = _('Mensaje de voz')
			elif obj.name == 'WhatsApp.ChatListArchiveButtonCellVm':
				obj.name = _('Chats Archivados')
			elif obj.UIAAutomationId == 'BackButton':
				obj.name = _('Atrás')
		except:
			pass
		try:
			if self.viewConfig == 'desactivado': return
			if obj.UIAAutomationId == 'BubbleListItem':
				obj.name = sub(r'\+\d[()\d\s‬-]{12,}', '', obj.name)
		except:
			pass

	def event_gainFocus(self, obj, nextHandler):
		try:
			if obj.UIAAutomationId == 'ChatsListItem':
				self.lastChat = obj
				nextHandler()
				if not self.globalObject:
					self.globalObject = api.getForegroundObject().children[1]
					nextHandler
				else:
					nextHandler()
			else:
				nextHandler()
		except:
			nextHandler()

	@script(gesture="kb:control+r")
	def script_voiceMessage(self, gesture):
		focus = api.getFocusObject()
		for obj in self.globalObject.children:
			if obj.UIAAutomationId == 'PttSendButton':
				obj.doAction()
				playWaveFile(os.path.join(self.soundsPath, "send.wav"))
				focus.setFocus()
				self.clearGestureBindings()
				self.bindGestures(self.__gestures)
				return
		for obj in self.globalObject.children:
			if obj.UIAAutomationId == 'RightButton':
				obj.doAction()
				playWaveFile(os.path.join(self.soundsPath, "start.wav"))
				focus.setFocus()
				self.bindGestures({"kb:control+shift+r": "cancelVoiceMessage", "kb:control+t": "timeAnnounce"})

	def script_cancelVoiceMessage(self, gesture):
		focus = api.getFocusObject()
		for obj in self.globalObject.children:
			if obj.UIAAutomationId == 'PttDeleteButton':
				obj.doAction()
				playWaveFile(os.path.join(self.soundsPath, "cancel.wav"))
				focus.setFocus()
				self.clearGestureBindings()
				self.bindGestures(self.__gestures)
				break

	def script_timeAnnounce(self, gesture):
		for obj in self.globalObject.children:
			if obj.UIAAutomationId == 'PttTimer':
				message(obj.name)
				break

	@script(gesture="kb:control+shift+e")
	def script_viewConfigToggle(self, gesture):
		self.configFile()
		with open(f"{appArgs.configPath}\\whatsapp.ini", "w") as f:
			if self.viewConfig == "activado":
				f.write("desactivado")
				self.viewConfig = "desactivado"
				# Translators: Mensaje que indica la desactivación de los mensajes editados
				message(_('Mensajes editados, desactivado'))
			else:
				f.write("activado")
				self.viewConfig = "activado"
				# Translators: Mensaje que anuncia la activación de los mensajes editados
				message(_('Mensajes editados, activado'))

	@script(gesture="kb:alt+rightArrow")
	def script_chatsList(self, gesture):
		if self.lastChat:
			self.lastChat.setFocus()

	@script(gesture="kb:alt+leftArrow")
	def script_switch(self, gesture):
		if self.switch == 'TextBox' or self.switch == None:
			for obj in self.globalObject.children:
				if obj.UIAAutomationId == 'ListView':
					obj.lastChild.setFocus()
					self.switch = 'ListView'
					break
		else:
			for obj in self.globalObject.children:
				if obj.UIAAutomationId == 'TextBox':
					obj.setFocus()
					self.switch = 'TextBox'
					break

	@script(gesture="kb:control+shift+t")
	def script_chatName(self, gesture):
		try:
			for obj in self.globalObject.children:
				if obj.UIAAutomationId == 'TitleButton':
					message(obj.firstChild.name)
					break
		except:
			pass

	@script(gesture="kb:alt+r")
	def script_responseText(self, gesture):
		fc = api.getFocusObject()
		if fc.UIAAutomationId == 'BubbleListItem':
			text = "\n".join([item.name for item in fc.children if item.UIAAutomationId == 'TextBlock'])
			message(text)

