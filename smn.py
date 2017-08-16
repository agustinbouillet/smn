# -*- coding: utf-8 -*-
# !/Library/Frameworks/Python.framework/Versions/3.4/bin/python3.4

import json
import os
import pwd
import re
import time
import urllib.request

import schedule
from bs4 import BeautifulSoup
from django.template.defaultfilters import slugify


class ServicioMeteorologicoNacional():
    # Ruta del servicio
    meses = {
        'enero': '01',
        'febrero': '02',
        'marzo': '03',
        'abril': '04',
        'mayo': '05',
        'junio': '06',
        'julio': '07',
        'agosto': '08',
        'septiembre': '09',
        'octubre': '10',
        'noviembre': '11',
        'diciembre': '12',
    }

    def __init__(self, **kwargs):
        self.ciudad = kwargs['ciudad']
        self.provincia = kwargs['provincia']


    def informe_meteorologico(self, **kwargs):
        url = 'http://www.smn.gov.ar/mobile/estado_movil.php?ciudad=%s' % (
            self.ciudad
        )
        html = urllib.request.urlopen(url)
        output = html.read().decode(html.headers.get_content_charset())

        # HTML parser
        soup = BeautifulSoup(output, 'lxml')
        data = soup.findAll('td')
        mobile_url = "http://www.smn.gov.ar/mobile/"

        # SRC de la imagen
        img_src = soup.find('img').get('src')

        # Obtengo la informacion de la imagen
        img = re.findall(r"\/?iconos_(dia|noche)\/(?:(\w*).png)", img_src)

        # Obtengo la informacion sobre la actualizacion
        actualizacion_pattern = re.compile(
            r"(3[0-1]|[0-2][\d]|[\d])[^\d]*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)[^\d]*([\d]{4})[^\d]*(?:(2[0-3]|[0-1][\d]|[\d])\s*:\s*([0-5]?[\d]))?",
            re.IGNORECASE)
        actualizacion = re.findall(
            actualizacion_pattern,
            soup.find('p').get_text()
        )

        # Timestamp de la fecha de actualizacion
        timestamp_actualizacion = "{0}-{1}-{2}T{3}:{4}:00".format(
            actualizacion[0][2],
            self.meses[actualizacion[0][1].lower()],
            actualizacion[0][0],
            actualizacion[0][3],
            actualizacion[0][4]
        )

        # Viento
        viento = re.sub(
            r"([\w]+)\s*(\d)+(\s)*([\w\/]*)", r"\1 \2\4", data[15].get_text()
        )

        # Sensación térmica
        sensacion_termica = re.sub(
            r"([\d\.]+)\s*(\°C)", r"\1\2", data[7].get_text()
        )

        a = {
            'region': data[0].get_text(),
            'temperatura': data[2].get_text(),
            'descripcion': data[4].get_text(),
            'sensacion-termica': sensacion_termica,
            'visibilidad': re.sub(r"\s", '', data[9].get_text()),
            'humedad': re.sub(r"\s", '', data[11].get_text()),
            'presion': re.sub(r"\s", '', data[13].get_text()),
            'viento': viento,
            'alias': img[0][1],
            'rotacion': img[0][0],
            'imagen': mobile_url + img_src,
            'timestamp-actualizacion': timestamp_actualizacion
        }

        return a

    def __sanitize_string(self, str):
        str = str.lower()
        items_to_search = ['area', 'areas', 'sensacion', 'termica']
        items_to_replace = ['área', 'áreas', 'sensación', 'térmica']

        c = 0
        nuevo_string = str
        while c <= len(items_to_search) - 1:
            nuevo_string = re.sub(items_to_search[c], items_to_replace[c],
                                  nuevo_string)
            c += 1

        return nuevo_string


    def __capitalize_string(self, str):
        """
        Capitaliza las oraciones de un string.
        :param str:
        :return: string
        """
        str = self.__sanitize_string(str)
        return '. '.join([txt.capitalize() for txt in str.split('. ')])



    def informe_meteorologico_extendido(self):
        try:
            url = 'http://www.smn.gov.ar/mobile/pronostico_movil.php?provincia=%s&ciudad=%s' % (
                self.provincia, self.ciudad
            )
            html = urllib.request.urlopen(url)
            output = html.read().decode(html.headers.get_content_charset())

            # HTML parser
            soup = BeautifulSoup(output, 'lxml')

            # REGEX para obtener el alias de las imagenes
            img_pattern = re.compile(
                r'(?P<alias>[\w\-\.\@]+).(png|jpg|gif|jpeg|svg)', 
                re.IGNORECASE
            )

            # Obtento la informacion detallada de la mañana y la noche
            descripcion_hoy = soup.find(
                "div", {"data-role": "collapsible"}
            ).find_all('h5')

            count = 0
            info = dict()
            while count <= len(descripcion_hoy) - 1:
                descripcion = descripcion_hoy[count]
                src = descripcion.find('img').get('src')
                search = re.search(img_pattern, src)
                alias = search.group('alias')

                info.update({
                    "descripcion-{0}".format(
                        slugify(
                            descripcion.get_text())): self.__capitalize_string(
                        descripcion.findNext(
                            'p').get_text()),
                    "alias-{0}".format(slugify(descripcion.get_text())): alias,
                })

                count += 1

            data = soup.findAll('table')
            data_tabla_hoy = data[1]
            valor = data_tabla_hoy.find_all('tr')

            for x in valor:
                n = x.find_all('td')
                info.update({
                    slugify(n[0].get_text()): n[1].get_text().strip()
                })

            return info
        except ValueError:
            print('No es posible obtener el informe extendido')
            print(ValueError)
            return dict()


if __name__ == "__main__":
	p = pwd.getpwuid(os.getuid())
	pwd_name = p.pw_name

	locaciones = [
		{'ciudad': 'Buenos_Aires', 'provincia': 0},
		{'ciudad': 'Aeroparque_Buenos_Aires', 'provincia': 0},
		{'ciudad': 'Mar_del_Plata', 'provincia': 1},
		{'ciudad': 'La_Plata', 'provincia': 1},
		#{'ciudad': 'Chascomus', 'provincia':1}
	]


	def cron():
		informe = list()
		try:
			for locacion in locaciones:
				smn = ServicioMeteorologicoNacional(
				ciudad=locacion['ciudad'],
				provincia=locacion['provincia']
				)
				data = dict()
				data.update(smn.informe_meteorologico())
				data.update(smn.informe_meteorologico_extendido())

				informe.append(data)

			# Compilo el json
			json_data = json.dumps(informe)

			# Crea el archivo json
			obj = open('smn.json','w')
			obj.write(json_data)
			obj.close()
			print('JSON generado exitosamente')
		except:
			print('No se puede obtener las definiciones del tiempo')

	cron()
	schedule.every(1).minutes.do(cron)

	while True:
		schedule.run_pending()
		time.sleep(1)
