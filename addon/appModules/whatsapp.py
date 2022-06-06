# -*- coding: utf-8 -*-
# Copyright (C) 2021 Gerardo Kessler <ReaperYOtrasYerbas@gmail.com>
# This file is covered by the GNU General Public License.

from threading import Thread
from time import sleep
import speech
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

def mute(time, msg= False):
	if msg:
		message(msg)
		sleep(0.1)
	Thread(target=killSpeak, args=(time,), daemon= True).start()

def killSpeak(time):
	speech.setSpeechMode(speech.SpeechMode.off)
	sleep(time)
	speech.setSpeechMode(speech.SpeechMode.talk)

class AppModule(appModuleHandler.AppModule):

	# Translators: Nombre de categoría en el diálogo gestos de entrada
	category = _('whatsapp')

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		self.lastChat = None
		self.soundsPath = os.path.join(appArgs.configPath, "addons", "whatsapp", "appModules", "sounds")
		self.configFile()

	def configFile(self):
		try:
			with open(f"{appArgs.configPath}\\whatsapp.ini", "r") as f:
				self.viewConfig = f.read()
		except FileNotFoundError:
			with open(f"{appArgs.configPath}\\whatsapp.ini", "w") as f:
				f.write("desactivado")

	def get(self, id):
		for obj in api.getForegroundObject().children[1].children:
			if obj.UIAAutomationId == id:
				return obj

	def event_NVDAObject_init(self, obj):
		try:
			if obj.UIAAutomationId == 'RightButton' and obj.previous.description == '':
				# Translators: Etiqueta del botón mensaje de voz
				obj.name = _('Mensaje de voz')
			elif obj.name == 'WhatsApp.ChatListArchiveButtonCellVm':
				# Translators: Etiqueta del elemento mensajes archivados
				obj.name = _('Chats Archivados')
			elif obj.UIAAutomationId == 'BackButton':
				# Translators: Etiqueta del botón atrás en los chatsArchivados
				obj.name = _('Atrás')
			elif obj.UIAAutomationId == 'PttDeleteButton':
				# Translators: Etiqueta del botón cancelar mensaje de voz
				obj.name = _('Cancelar mensaje')
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
			else:
				nextHandler()
		except:
			nextHandler()

	@script(
	category= category,
	# Translators: Descripción del elemento en el diálogo gestos de entrada
	description= _('Iniciar o finalizar la grabación de un mensaje de voz'),
		gesture= 'kb:control+r'
	)
	def script_voiceMessage(self, gesture):
		textBox = self.get('TextBox')
		button = self.get('RightButton') or self.get('PttSendButton')
		if button and (textBox is None or textBox.childCount > 0):
			button.doAction()
			mute(1)
			if button.UIAAutomationId == 'RightButton':
				playWaveFile(os.path.join(self.soundsPath, "start.wav"))
				return
			else:
				playWaveFile(os.path.join(self.soundsPath, "send.wav"))

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Cancela la grabación de los mensajes de voz'),
		gesture= 'kb:control+shift+r'
	)
	def script_cancelVoiceMessage(self, gesture):
		cancel = self.get('PttDeleteButton')
		if cancel:
			cancel.doAction()
			playWaveFile(os.path.join(self.soundsPath, "cancel.wav"))
		else:
			gesture.send()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza el tiempo de grabación de un mensaje'),
		gesture= 'kb:control+t'
	)
	def script_timeAnnounce(self, gesture):
		timer = self.get('PttTimer')
		if timer:
			message(timer.name)

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Activa y desactiva la eliminación de los números de teléfono de los contactos no agendados en los mensajes'),
		gesture= 'kb:control+shift+e'
	)
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

	@script(
	category= category,
	# Translators: Descripción del elemento en el diálogo gestos de entrada
	description= _('Enfoca la lista de chats'),
		gesture= 'kb:alt+rightArrow'
	)
	def script_chatsList(self, gesture):
		if self.lastChat:
			self.lastChat.setFocus()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Conmuta entre la lista de mensajes y el cuadro de edición dentro de un chat'),
		gesture= 'kb:alt+leftArrow'
	)
	def script_switch(self, gesture):
		if api.getFocusObject().UIAAutomationId == 'BubbleListItem':
			textBox = self.get('TextBox')
			if textBox:
				textBox.setFocus()
		else:
			listView = self.get('ListView')
			if listView:
				listView.lastChild.setFocus()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza el nombre del contacto o grupo'),
		gesture= 'kb:control+shift+t'
	)
	def script_chatName(self, gesture):
		title = self.get('TitleButton')
		if title:
			message(title.firstChild.name)

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza la respuesta en el mensaje con el foco'),
		gesture= 'kb:alt+r'
	)
	def script_responseText(self, gesture):
		fc = api.getFocusObject()
		if fc.UIAAutomationId == 'BubbleListItem':
			text = "\n".join([item.name for item in fc.children if item.UIAAutomationId == 'TextBlock'])
			message(text)

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón adjuntar'),
		gesture= 'kb:control+shift+a'
	)
	def script_toAttach(self, gesture):
		attach = self.get('AttachButton')
		if attach:
			message(attach.name)
			attach.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón info del chat'),
		gesture= 'kb:control+shift+i'
	)
	def script_moreInfo(self, gesture):
		info = self.get('TitleButton')
		if info:
			message(info.name)
			info.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón de configuración'),
		gesture= 'kb:control+shift+o'
	)
	def script_settings(self, gesture):
		settings = self.get('SettingsButton')
		if settings:
			message(settings.name)
			settings.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón de nuevo chat'),
		gesture= 'kb:control+shift+n'
	)
	def script_newChat(self, gesture):
		newChat = self.get('NewConvoButton')
		if newChat:
			message(newChat.name)
			newChat.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón llamada de video'),
		gesture= 'kb:control+shift+v'
	)
	def script_videoCall(self, gesture):
		videoCall = self.get('VideoCallButton')
		if videoCall:
			message(videoCall.name)
			videoCall.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón llamada de audio'),
		gesture= 'kb:control+shift+l'
	)
	def script_audioCall(self, gesture):
		audioCall = self.get('AudioCallButton')
		if audioCall:
			message(audioCall.name)
			audioCall.doAction()
