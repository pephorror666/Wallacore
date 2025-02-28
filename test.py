import streamlit as st
import pandas as pd
import csv
from PIL import Image
import requests
from io import BytesIO
import pyperclip
from datetime import datetime
import os
import json
import base64

# Función para verificar las credenciales del usuario
def verificar_credenciales(usuario, password):
    if usuario in st.secrets:
        if st.secrets[usuario]["password"] == password:
            return True, st.secrets[usuario]["correo"]
    return False, None

# Función para cargar el catálogo de productos
def cargar_catalogo():
    return pd.read_csv('catalogo.csv', encoding='utf-8')

# Función para redimensionar la imagen
def redimensionar_imagen(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img.thumbnail((100, 100))
        return img
    except:
        return None

# Función para mostrar la lista de productos
def mostrar_productos(df, titulo, es_mis_productos=False):
    st.header(titulo)
    for index, row in df.iterrows():
        with st.expander(f"{row['Producto']} - {row['Precio']}€"):
            st.write(f"Vendedor: {row['Vendedor']}")
            st.write(f"Descripción: {row['Descripción']}")
            img = redimensionar_imagen(row['Foto'])
            if img:
                st.image(img, caption=row['Producto'])
            else:
                st.write("No se pudo cargar la imagen")
            
            if not es_mis_productos:
                col1, col2 = st.columns(2)
                if col1.button(f"Copiar correo del vendedor {index}"):
                    pyperclip.copy(row['Correo Vendedor'])
                    st.success("Correo copiado al portapapeles")
                if col2.button(f"Enviar mensaje al vendedor {index}"):
                    st.session_state.producto_seleccionado = row['Producto']
                    st.session_state.vendedor_seleccionado = row['Vendedor']
                    st.session_state.correo_vendedor = row['Correo Vendedor']
                    st.rerun()
            else:
                if st.button(f"Eliminar producto {index}"):
                    eliminar_producto(index)
                    st.rerun()

# Función para añadir un nuevo producto
def añadir_producto(vendedor, correo, producto, descripcion, foto_url, precio):
    with open('catalogo.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([vendedor, correo, producto, descripcion, foto_url, precio])

# Función para eliminar un producto
def eliminar_producto(index):
    df = cargar_catalogo()
    df = df.drop(index)
    df.to_csv('catalogo.csv', index=False, encoding='utf-8')

# Función para enviar un mensaje
def enviar_mensaje(remitente, destinatario, producto, mensaje):
    if not os.path.exists('mensajes.csv'):
        with open('mensajes.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['fecha', 'remitente', 'destinatario', 'producto', 'mensaje'])
    
    with open('mensajes.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), remitente, destinatario, producto, mensaje])

# Función para cargar los mensajes de un usuario
def cargar_mensajes(usuario):
    mensajes = []
    if os.path.exists('mensajes.csv'):
        with open('mensajes.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Saltar la fila de encabezados
            for row in reader:
                if row[1] == usuario or row[2] == usuario:  # Si el usuario es el remitente o el destinatario
                    mensajes.append(row)
    # Ordenar los mensajes por fecha, del más reciente al más antiguo
    mensajes.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M"), reverse=True)
    return mensajes

# Función para eliminar un mensaje
def eliminar_mensaje(index):
    df = pd.read_csv('mensajes.csv')
    df = df.drop(index)
    df.to_csv('mensajes.csv', index=False, encoding='utf-8')

# Función para contar mensajes no leídos
def contar_mensajes_no_leidos(usuario):
    mensajes = cargar_mensajes(usuario)
    return len([m for m in mensajes if m[2] == usuario])

# Función para subir la imagen a Imgur
def upload_to_imgur(image_file, client_id):
    try:
        img_str = base64.b64encode(image_file.read()).decode()
        headers = {'Authorization': f'Client-ID {client_id}'}
        data = {'image': img_str}
        response = requests.post('https://api.imgur.com/3/image', headers=headers, data=data)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        st.write(f"Imgur API Response: {response.json()}")  # Imprime la respuesta completa
        return response.json()['data']['link']
    except requests.exceptions.RequestException as e:
        st.error(f"Error al subir la imagen a Imgur: {e}")
        st.error(f"Request Exception: {e}")  # Imprime detalles de la excepción
        return None
    except KeyError as e:
        st.error(f"Error al procesar la respuesta de Imgur: {e}")
        st.error(f"Response: {response.text}")  # Imprime el texto de la respuesta
        return None

# Configuración de la página
st.set_page_config(page_title="Wallacore", layout="wide")

# Inicialización de la sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario = None
    st.session_state.correo = None
    st.session_state.producto_seleccionado = None
    st.session_state.vendedor_seleccionado = None
    st.session_state.correo_vendedor = None

# Página de inicio de sesión
if not st.session_state.logged_in:
    st.title("Bienvenido a Wallacore")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        verificado, correo = verificar_credenciales(usuario, password)
        if verificado:
            st.session_state.logged_in = True
            st.session_state.usuario = usuario
            st.session_state.correo = correo
            st.success("Inicio de sesión exitoso")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

# Página principal después del inicio de sesión
else:
    st.sidebar.title(f"Bienvenido, {st.session_state.usuario}")
    mensajes_no_leidos = contar_mensajes_no_leidos(st.session_state.correo)
    menu = st.sidebar.radio("Menú", [
        "Lista de productos", 
        "Mis productos", 
        "Poner producto a la venta", 
        f"Mis mensajes ({mensajes_no_leidos} nuevos)" if mensajes_no_leidos > 0 else "Mis mensajes"
    ])

    if menu == "Lista de productos":
        if st.session_state.producto_seleccionado:
            st.subheader(f"Enviar mensaje sobre: {st.session_state.producto_seleccionado}")
            mensaje = st.text_area("Escribe tu mensaje")
            if st.button("Enviar mensaje"):
                enviar_mensaje(st.session_state.correo, st.session_state.correo_vendedor, st.session_state.producto_seleccionado, mensaje)
                st.success("Respuesta enviada con éxito")
                st.session_state.producto_seleccionado = None
                st.session_state.vendedor_seleccionado = None
                st.session_state.correo_vendedor = None
                st.rerun()
        else:
            df = cargar_catalogo()
            mostrar_productos(df, "Productos disponibles")

    elif menu == "Mis productos":
        df = cargar_catalogo()
        mis_productos = df[df['Correo Vendedor'] == st.session_state.correo]
        mostrar_productos(mis_productos, "Mis productos a la venta", es_mis_productos=True)

    elif menu == "Poner producto a la venta":
        st.header("Poner producto a la venta")
        producto = st.text_input("Nombre del producto")
        descripcion = st.text_area("Descripción")
        foto = st.file_uploader("Subir foto del producto", type=["png", "jpg", "jpeg"])
        precio = st.number_input("Precio (€)", min_value=0.0, step=0.01)

        if st.button("Publicar producto"):
            if foto is not None:
                # Configura tu Client ID de Imgur desde los secrets de Streamlit
                IMGUR_CLIENT_ID = st.secrets["imgur_client_id"]

                # Subir la imagen a Imgur
                foto_url = upload_to_imgur(foto, IMGUR_CLIENT_ID)

                if foto_url:
                    añadir_producto(st.session_state.usuario, st.session_state.correo, producto, descripcion, foto_url, precio)
                    st.success("Producto añadido con éxito")
                    st.rerun()
                else:
                    st.error("Hubo un error al subir la imagen. Inténtalo de nuevo.")
            else:
                st.error("Por favor, sube una foto del producto.")

    elif menu.startswith("Mis mensajes"):
        st.header("Mis mensajes")
        mensajes = cargar_mensajes(st.session_state.correo)
        if not mensajes:
            st.write("No se han encontrado mensajes")
        else:
            for index, mensaje in enumerate(mensajes):
                es_enviado = mensaje[1] == st.session_state.correo
                tipo_mensaje = "Enviado" if es_enviado else "Recibido"
                
                titulo = f"{tipo_mensaje}: Mensaje sobre {mensaje[3]} {'para' if es_enviado else 'de'} {mensaje[2] if es_enviado else mensaje[1]}"
                
                with st.expander(titulo):
                    st.write(f"Fecha: {mensaje[0]}")
                    st.write(f"{'Para' if es_enviado else 'De'}: {mensaje[2] if es_enviado else mensaje[1]}")
                    st.write(f"Producto: {mensaje[3]}")
                    st.write(f"Mensaje: {mensaje[4]}")
                    
                    if not es_enviado:  # Solo mostrar opciones para mensajes recibidos
                        col1, col2 = st.columns(2)
                        if col1.button(f"Eliminar mensaje {index}"):
                            eliminar_mensaje(index)
                            st.rerun()
                        if col2.button(f"Responder mensaje {index}"):
                            st.session_state.respondiendo_mensaje = index
                            st.session_state.destinatario_respuesta = mensaje[1]
                            st.session_state.producto_respuesta = mensaje[3]
                            st.rerun()

        if hasattr(st.session_state, 'respondiendo_mensaje'):
            st.subheader(f"Responder al mensaje sobre: {st.session_state.producto_respuesta}")
            respuesta = st.text_area("Escribe tu respuesta")
            if st.button("Enviar respuesta"):
                enviar_mensaje(st.session_state.correo, st.session_state.destinatario_respuesta, st.session_state.producto_respuesta, respuesta)
                st.success("Respuesta enviada con éxito")
                del st.session_state.respondiendo_mensaje
                del st.session_state.destinatario_respuesta
                del st.session_state.producto_respuesta
                st.rerun()

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.usuario = None
        st.session_state.correo = None
        st.session_state.producto_seleccionado = None
        st.session_state.vendedor_seleccionado = None
        st.session_state.correo_vendedor = None
        st.rerun()
