class CircularList(list):
	def __init__(self, size):
		self.__size=size

	def append(self, e):
		if len(self)<self.__size:
			super().append(e)
		else:
			super().append(e)
			self.pop(0)

	