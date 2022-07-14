# -*- coding: utf-8 -*-
# Copyright (C) 2021 Gerardo Kessler <ReaperYOtrasYerbas@gmail.com>
# This file is covered by the GNU General Public License.

from threading import Thread
from time import sleep
import speech
from globalVars import appArgs
import appModuleHandler
from scriptHandler import script
import wx
import api
import winUser
import config
from ui import message
from nvwave import playWaveFile
from re import search, sub
import os
import addonHandler

# Lína de traducción
addonHandler.initTranslation()

# Funciones de lectura y escritura de las configuraciones del complemento
def initConfiguration():
	confspec = {
		'RemovePhoneNumberInMessages':'boolean(default=False)',
	}
	config.conf.spec['WhatsAppBeta'] = confspec

def getConfig(key):
	return config.conf["WhatsAppBeta"][key]

def setConfig(key, value):
	try:
		config.conf.profiles[0]["WhatsAppBeta"][key] = value
	except:
		config.conf["WhatsAppBeta"][key] = value

initConfiguration()

# Función para romper la cadena de verbalización y callar al sintetizador durante el tiempo especificado
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
		# Translators: Mensaje que anuncia que no se ha encontrado el elemento
		self.notFound = _('Elemento no encontrado')
		self.lastChat = None
		self.soundsPath = os.path.join(appArgs.configPath, 'addons', 'whatsapp', 'sounds')
		self.temp_value = getConfig('RemovePhoneNumberInMessages')

	# Función que recibe el UIAAutomationId por parámetro, y devuelve el objeto de coincidencia
	def get(self, id, errorMessage, gesture):
		for obj in api.getForegroundObject().children[1].children:
			if obj.UIAAutomationId == id:
				return obj
		if errorMessage:
			message(self.notFound)
		if gesture:
			gesture.send()

	def event_NVDAObject_init(self, obj):
		try:
			if obj.UIAAutomationId == 'RightButton' and obj.previous.description == '':
				# Translators: Etiqueta del botón mensaje de voz
				obj.name = _('Mensaje de voz')
			elif obj.name == 'WhatsApp.ChatListArchiveButtonCellVm':
				# Translators: Etiqueta del elemento mensajes archivados
				obj.name = _('Chats Archivados')
			elif obj.name == '\ue76e' and obj.value == None:
				obj.name = _('Reaccionar')
			elif obj.UIAAutomationId == 'BackButton':
				# Translators: Etiqueta del botón atrás en los chatsArchivados
				obj.name = _('Atrás')
			elif obj.UIAAutomationId == 'PttDeleteButton':
				# Translators: Etiqueta del botón cancelar mensaje de voz
				obj.name = _('Cancelar mensaje')
			elif obj.name == '\ue8bb':
				obj.name = _('Cancelar respuesta')
			elif obj.UIAAutomationId == "SendMessages":
				obj.name = _(obj.previous.name+": "+obj.firstChild.name)
			elif obj.UIAAutomationId == "EditInfo":
				obj.name = _(obj.previous.name+": "+obj.firstChild.name)
			elif obj.UIAAutomationId == "MuteDropdown":
				obj.name = obj.children[0].name
			elif obj.UIAAutomationId == "ThemeCombobox":
				obj.name = obj.previous.name + obj.firstChild.children[1].name
			elif obj.name == 'WhatsApp.Design.ThemeData':
				obj.name = obj.children[1].name
			elif obj.UIAAutomationId == 'PttPauseButton':
				# Translators: Etiqueta del botón pausar grabación
				obj.name = _('Pausar grabación')
			elif obj.UIAAutomationId == 'PttSendButton':
				# Translators: Etiqueta del botón Enviar mensaje de voz
				obj.name = _('Enviar mensaje de voz')
		except:
			pass
		try:
			if not self.temp_value: return
			if obj.UIAAutomationId == 'BubbleListItem':
				obj.name = sub(r'\+\d[()\d\s‬-]{12,}', '', obj.name)
		except:
			pass

	def event_gainFocus(self, obj, nextHandler):
		try:
			# Renombre del mensaje con documento adjunto por el texto de los objetos que tienen el nombre el archivo, tipo y tamaño
			if obj.UIAAutomationId == 'BubbleListItem' and (obj.children[1].UIAAutomationId == 'NameTextBlock' or obj.children[3].UIAAutomationId == 'NameTextBlock' or obj.children[4].UIAAutomationId == 'NameTextBlock'):
				for data in obj.children:
					if data.UIAAutomationId == 'NameTextBlock':
						obj.name = '{} {}'.format(data.name, data.next.name)
			else:
				nextHandler()
		except:
			nextHandler()
		try:
			if obj.UIAAutomationId == 'ChatsListItem':
				self.lastChat = obj
			else:
				nextHandler()
		except:
			nextHandler()

	@script(gesture="kb:space")
	def script_playPause(self, gesture):
		focus = api.getFocusObject()
		try:
			if focus.children[1].UIAAutomationId == 'IconTextBlock':
				api.moveMouseToNVDAObject(focus.children[1])
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
			else:
				gesture.send()
		except:
			gesture.send()

	@script(
	category= category,
	# Translators: Descripción del elemento en el diálogo gestos de entrada
	description= _('Iniciar o finalizar la grabación de un mensaje de voz'),
		gesture= 'kb:control+r'
	)
	def script_voiceMessage(self, gesture):
		send = self.get('PttSendButton', False, None)
		if send:
			send.doAction()
			playWaveFile(os.path.join(self.soundsPath, 'send.wav'))
			return
		record = self.get('RightButton', True, gesture)
		if record:
			record.doAction()
			mute(1)
			playWaveFile(os.path.join(self.soundsPath, 'start.wav'))

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
			playWaveFile(os.path.join(self.soundsPath, 'cancel.wav'))

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
		description= _('Activa y desactiva la eliminación de los números de teléfono de los contactos no agendados en los mensajes'),
		gesture= 'kb:control+shift+e'
	)
	def script_viewConfigToggle(self, gesture):
		if self.temp_value:
			setConfig('RemovePhoneNumberInMessages', False)
			self.temp_value = False
			# Translators: Mensaje que indica la desactivación de los mensajes editados
			message(_('Mensajes editados, desactivado'))
		else:
			setConfig('RemovePhoneNumberInMessages', True)
			self.temp_value = True
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
			textBox = self.get('TextBox', False, None)
			if textBox:
				textBox.setFocus()
		else:
			listView = self.get('ListView', False, None)
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
			message(' '.join([obj.name for obj in title.children if len(obj.name) < 50]))

	@script(
		category= category,
		# Translators: Descripción del elemento en el diálogo gestos de entrada
		description= _('Verbaliza la respuesta en el mensaje con el foco'),
		gesture= 'kb:alt+r'
	)
	def script_responseText(self, gesture):
		fc = api.getFocusObject()
		if fc.UIAAutomationId == 'BubbleListItem':
			text = '\n'.join([item.name for item in fc.children if item.UIAAutomationId == 'TextBlock'])
			message(text)

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
		description= _('Pulsa el botón de configuración'),
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
		description= _('Pulsa el botón de nuevo chat'),
		gesture= 'kb:control+shift+n'
	)
	def script_newChat(self, gesture):
		newChat = self.get('NewConvoButton', True, gesture)
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
		playWaveFile(os.path.join(self.soundsPath, 'open.wav'))
		wx.LaunchDefaultBrowser('file://' + addonHandler.Addon(os.path.join(appArgs.configPath, "addons", "whatsapp")).getDocFilePath(), flags=0)
		# except:
			# message(self.notFound)
