from settings import functions, config

s = functions.create_local_socket(config.LOCAL_SOCKET_URL)
s.send('hi')