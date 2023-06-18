# -*- coding: utf-8 -*-
# Copyright (C) 2021 Gerardo Kessler <ReaperYOtrasYerbas@gmail.com>
# This file is covered by the GNU General Public License.
# Colaboraciones importantes de Williams Cuevas

import webbrowser
from threading import Thread
from time import sleep
import speech
from keyboardHandler import KeyboardInputGesture
from globalVars import appArgs
import appModuleHandler
from scriptHandler import script
import wx
import api
import winUser
import config
from ui import message, browseableMessage
from nvwave import playWaveFile
import re
from re import search, sub
import sys
import os
dirAddon = os.path.dirname(__file__)
sys.path.append(dirAddon)
sys.path.append(os.path.join(dirAddon, "lib"))
import emoji
emoji.__path__.append(os.path.join(dirAddon, "lib", "emoji"))
del sys.path[-2:]
import NVDAObjects
import addonHandler

# Lína de traducción
addonHandler.initTranslation()

# Funciones de lectura y escritura de las configuraciones del complemento
def initConfiguration():
	confspec = {
		'RemovePhoneNumberInMessages':'boolean(default=False)',
		'AddonSounds':'boolean(default=True)',
		'RemoveEmojis':'boolean(default=False)'
	}
	config.conf.spec['WhatsApp'] = confspec

def getConfig(key):
	return config.conf["WhatsApp"][key]

def setConfig(key, value):
	try:
		config.conf.profiles[0]["WhatsApp"][key] = value
	except:
		config.conf["WhatsApp"][key] = value

initConfiguration()

# Función para romper la cadena de verbalización y callar al sintetizador durante el tiempo especificado
def mute(time, msg= False):
	if msg:
		message(msg)
		sleep(0.1)
	Thread(target=killSpeak, args=(time,), daemon= True).start()

def killSpeak(time):
	if speech.getState().speechMode == speech.SpeechMode.off: return
	speech.setSpeechMode(speech.SpeechMode.off)
	sleep(time)
	speech.setSpeechMode(speech.SpeechMode.talk)

# Ruta de la carpeta con los sonidos
sounds_path = os.path.join(dirAddon, 'sounds')

class AppModule(appModuleHandler.AppModule):

	category = 'whatsapp'

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		# Translators: Mensaje que anuncia que no se ha encontrado el elemento
		self.not_found = _('Elemento no encontrado')
		self.last_chat = None
		self.message_list = None
		self.message_object = None
		self.remove_phone_number = getConfig('RemovePhoneNumberInMessages')
		self.addon_sounds = getConfig('AddonSounds')
		self.remove_emojis = getConfig('RemoveEmojis')

	# Función que recibe el UIAAutomationId por parámetro, y devuelve el objeto de coincidencia
	def get(self, id, errorMessage, gesture):
		for obj in api.getForegroundObject().children[1].children[0].children:
			try:
				if obj.UIAAutomationId == id:
					return obj
			except:
				pass
		if errorMessage:
			message(self.not_found)
		if gesture:
			gesture.send()

	def event_NVDAObject_init(self, obj):
		try:
			if obj.UIAAutomationId == 'ChatsListItem':
				self.last_chat = obj
				return
		except:
			pass
		try:
			if obj.UIAAutomationId != 'BubbleListItem' or not self.remove_phone_number and not self.remove_emojis: return
			if self.remove_phone_number:
				obj.name = sub(r'\+\d[()\d\s‬-]{12,}', '', obj.name)
			if self.remove_emojis:
				print(emoji.emoji_count(obj.name))
				obj.name = emoji.replace_emoji(obj.name, '')
		except:
			pass
		try:
			for element in obj.children:
				try:
					if element.UIAAutomationId == 'ProgressRing':
						pattern= search(r'\d\d:\d\d\s[pa]\.\sm\.', obj.name)
						obj.name = obj.name.replace(pattern[0], f'{element.next.name} ({pattern[0]})')
					if element.UIAAutomationId == 'ForwardedHeader':
						obj.name = f'Reenviado: {obj.name}'
					if element.UIAAutomationId == 'ReactionBubble':
						obj.name = f'{obj.name} ({element.name})'
				except:
					pass
		except:
			pass

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		try:
			if obj.UIAAutomationId == 'BubbleListItem':
				clsList.insert(0, Messages)
		except:
			pass

	@script(gestures=[f'kb:alt+{i}' for i in range(1, 10)])
	def script_lastMessages(self, gesture):
		x = int(gesture.displayName[-1])
		if not self.message_list:
			self.message_list = self.get('MessagesList', False, None)
		count = self.message_list.UIAChildren.Length
		try:
			messageElement = self.message_list.UIAChildren.GetElement(count-x)
			self.message_object = NVDAObjects.UIA.UIA(UIAElement=messageElement)
			message(self.message_object.name)
		except:
			pass

	@script(gesture="kb:alt+enter")
	def script_messageFocus(self, gesture):
		try:
			self.message_object.setFocus()
		except:
			gesture.send()

	@script(
	category= category,
	# Translators: Descripción del elemento en el diálogo gestos de entrada
	description= _('Inicia o finaliza la grabación de un mensaje de voz'),
		gesture= 'kb:control+r'
	)
	def script_voiceMessage(self, gesture):
		focus= api.getFocusObject()
		send = self.get('PttSendButton', False, None)
		if send:
			send.doAction()
			# Translators: Mensaje de envío del mensaje de audio
			if not self.addon_sounds: message(_('Enviando...'))
			if self.addon_sounds: playWaveFile(os.path.join(sounds_path, 'sending.wav'))
			mute(0.1)
			return
		record = self.get('RightButton', True, gesture)
		if record:
			if record.previous.description == '':
				# Translators: Mensaje de inicio de grabación de un mensaje de voz
				if not self.addon_sounds: message(_('Grabando'))
				if self.addon_sounds: playWaveFile(os.path.join(sounds_path, 'recording.wav'))
				record.doAction()
				mute(1)
				Thread(target=self.sendGesture, args=('shift+tab', 2), daemon=True).start()
			else:
				# Translators: Aviso de que el cuadro de edición de mensaje no está vacío
				message(_('El cuadro de edición no está vacío'))

	def sendGesture(self, kb, amount):
		sleep(0.5)
		for x in range(amount):
			KeyboardInputGesture.fromName(kb).send()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Cancela la grabación de los mensajes de voz'),
		gesture= 'kb:control+shift+r'
	)
	def script_cancelVoiceMessage(self, gesture):
		cancel = self.get('PttDeleteButton', False, gesture)
		if cancel:
			cancel.doAction()
			# Translators: Mensaje de cancelación de la grabación de un mensaje de voz
			if not self.addon_sounds: message(_('Cancelado'))
			if self.addon_sounds: playWaveFile(os.path.join(sounds_path, 'cancel.wav'))
			mute(0.1)

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza el tiempo de grabación de un mensaje'),
		gesture= 'kb:control+t'
	)
	def script_timeAnnounce(self, gesture):
		timer = self.get('PttTimer', False, gesture)
		if timer:
			message(timer.name)

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Activa y desactiva los sonidos del complemento'),
		gesture= 'kb:control+alt+s'
	)
	def script_soundsConfigToggle(self, gesture):
		if self.addon_sounds:
			setConfig('AddonSounds', False)
			self.addon_sounds = False
			# Translators: Mensaje que indica la desactivación de los sonidos del complemento
			message(_('Sonidos del complemento, desactivados'))
		else:
			setConfig('AddonSounds', True)
			self.addon_sounds = True
			# Translators: Mensaje que anuncia la activación de los sonidos del complemento
			message(_('Sonidos del complemento, activados'))

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Activa y desactiva la eliminación de los números de teléfono de los contactos no agendados en los mensajes'),
		gesture= 'kb:control+alt+n'
	)
	def script_viewNumbersToggle(self, gesture):
		if self.remove_phone_number:
			setConfig('RemovePhoneNumberInMessages', False)
			self.remove_phone_number = False
			# Translators: Mensaje de la opción de remover números telefónicos, desactivado
			message(_('Eliminar números telefónicos, desactivado'))
		else:
			setConfig('RemovePhoneNumberInMessages', True)
			self.remove_phone_number = True
			# Translators: Mensaje de la opción de remover números telefónicos, activado
			message(_('Eliminar números telefónicos, activado'))

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Activa y desactiva la opción para ocultar los emojis en los mensajes'),
		gesture= 'kb:control+alt+e'
	)
	def script_emojisToggle(self, gesture):
		if self.remove_emojis:
			setConfig('RemoveEmojis', False)
			self.remove_emojis = False
			# Translators: Mensaje de visualización de emojis, Desactivado
			message(_('Ocultar emojis, desactivado'))
		else:
			setConfig('RemoveEmojis', True)
			self.remove_emojis = True
			# Translators: Mensaje de visualización de emojis, activado
			message(_('Ocultar emojis, activado'))

	@script(
	category= category,
	# Translators: Descripción del elemento en el diálogo gestos de entrada
	description= _('Enfoca la lista de chats'),
		gesture= 'kb:alt+rightArrow'
	)
	def script_chatsList(self, gesture):
		if self.last_chat:
			self.last_chat.setFocus()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Enfoca el elemento mensajes no leídos'),
		gesture= 'kb:alt+downArrow'
	)
	def script_unreadFocus(self, gesture):
		messagesObject = self.message_list = self.get('MessagesList', False, None)
		if not messagesObject: return
		for obj in reversed(messagesObject.children):
			if obj.childCount == 1 and obj.firstChild.UIAAutomationId == '' and search(r'\d{1,3}\s\w+', obj.name):
				obj.setFocus()
				break

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Conmuta entre la lista de mensajes y el cuadro de edición dentro de un chat'),
		gesture= 'kb:alt+leftArrow'
	)
	def script_switch(self, gesture):
		if api.getFocusObject().UIAAutomationId == 'BubbleListItem':
			textBox = self.get('TextBox', False, None)
			if textBox:
				textBox.setFocus()
		else:
			listView = self.get('MessagesList', False, None)
			if listView:
				listView.lastChild.setFocus()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza el nombre del contacto o grupo'),
		gesture= 'kb:control+shift+t'
	)
	def script_chatName(self, gesture):
		title = self.get('TitleButton', True, gesture)
		if title:
			contact_name = ' '.join([obj.name for obj in title.children if len(obj.name) < 50])
			if self.remove_emojis:
				contact_name = emoji.replace_emoji(contact_name, '')
			message(contact_name)

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza la respuesta en el mensaje con el foco'),
		gesture= 'kb:alt+r'
	)
	def script_viewText(self, gesture):
		fc = api.getFocusObject()
		for i in range(fc.childCount):
			try:
				if fc.children[i].UIAAutomationId == 'OpenButton':
					message('{}; {}'.format(fc.children[i-2].name, fc.children[i-1].name))
					return
			except:
				pass
		try:
			if not fc.UIAAutomationId == 'BubbleListItem': return
			text = '\n'.join([item.name for item in fc.children if (item.UIAAutomationId == 'TextBlock' and item.next.next.UIAAutomationId == 'ReadMore')])
			if text:
				browseableMessage(text, _('Texto del mensaje'))
			else:
				# Translators: Mensaje de que no hay texto para mostrar
				message(_('No hay texto para mostrar'))
		except:
			pass

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón adjuntar'),
		gesture= 'kb:control+shift+a'
	)
	def script_toAttach(self, gesture):
		attach = self.get('AttachButton', True, gesture)
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
		info = self.get('TitleButton', True, gesture)
		if info:
			message(info.name)
			info.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Activa la ventana de filtros'),
		gesture= 'kb:control+shift+o'
	)
	def script_settings(self, gesture):
		settings = self.get('SettingsButton', True, gesture)
		if settings:
			message(settings.name)
			settings.doAction()

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Pulsa el botón llamada de video'),
		gesture= 'kb:control+shift+v'
	)
	def script_videoCall(self, gesture):
		videoCall = self.get('VideoCallButton', True, gesture)
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
		audioCall = self.get('AudioCallButton', True, gesture)
		if audioCall:
			message(audioCall.name)
			audioCall.doAction()

	@script(gesture="kb:f1")
	def script_help(self, gesture):
		# try:
		if self.addon_sounds: playWaveFile(os.path.join(sounds_path, 'open.wav'))
		wx.LaunchDefaultBrowser('file://' + addonHandler.Addon(os.path.join(appArgs.configPath, "addons", "whatsapp")).getDocFilePath(), flags=0)
		# except:
			# message(self.notFound)

class Messages():

	def initOverlayClass(self):
		self.progress = None
		self.play = None
		for obj in self.children:
			if obj.UIAAutomationId == 'Scrubber':
				self.progress = obj
			elif obj.UIAAutomationId == 'IconTextBlock':
				self.play = obj

		self.bindGestures({
			"kb:space": "playPause",
			"kb:control+space": "speed",
			"kb:alt+upArrow": "durationAudioAnnounce",
			"kb:control+enter": "linkOpen"
			})

	def script_playPause(self, gesture):
		if self.play:
			api.moveMouseToNVDAObject(self.play)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
			winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)

	def script_linkOpen(self, gesture):
		if search('https?://', self.name, re.I):
			webbrowser.open(search(r"https?://\S+", self.name, re.I)[0])
		else:
			gesture.send()

	def script_speed(self, gesture):
		for obj in self.children:
			if obj.UIAAutomationId == 'PlaybackSpeedButton':
				obj.doAction()
				self.setFocus()
				return
		# Translators: Mensaje que avisa de la inexistencia de mensajes en reproducción
		message(_('Ningún mensaje de audio en reproducción'))

	def script_durationAudioAnnounce(self, gesture):
		for obj in self.children:
			try:
				if obj.UIAAutomationId == 'ProgressRing':
					message(obj.next.name)
					break
			except:
				pass
