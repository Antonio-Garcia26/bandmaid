from http_vs_selenium import intento_http
res = intento_http('https://catalog.data.gov/dataset','health')
print(res['status_code'], res['tarjetas_detectadas'], res['tiempo_seg'])
