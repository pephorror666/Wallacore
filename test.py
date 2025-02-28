import streamlit as st
import pandas as pd
import csv
from PIL import Image
import requests
from io import BytesIO
import pyperclip
from datetime import datetime
import os
from nylas import Client
from nylas.models.drafts import CreateDraftRequest
#from nylas.models.messages import SendMessageRequest #Quitado ya que SendMessageRequest no se usa directamente

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
                    #st.experimental_rerun()
                    st.rerun()
            else:
                if st.button(f"Eliminar producto {index}"):
                    eliminar_producto(index)
                    #st.experimental_rerun()
                    st.rerun()

# Función para añadir un nuevo producto
def añadir_producto(vendedor, correo, producto, descripcion, foto, precio):
    with open('catalogo.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([vendedor, correo, producto, descripcion, foto, precio])

# Función para eliminar un producto
def eliminar_producto(index):
    df = cargar_catalogo()
    df = df.drop(index)
    df.to_csv('catalogo.csv', index=False, encoding='utf-8')

def enviar_correo(destinatario, asunto, cuerpo):
    # Credenciales de Nylas
    client_id = st.secrets["nylas"]["client_id"]
    client_secret = st.secrets["nylas"]["client_secret"]
    access_token = st.secrets["nylas"]["access_token"]
    remitente = st.secrets["email"]["remitente"]  # Direccion de correo electronico del remitente

    # Inicializa el cliente de Nylas
    nylas_client = Client(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
    )

    try:
        # Crear el borrador del mensaje
        create_request = CreateDraftRequest(
            to=[{"email": destinatario}],
            subject=asunto,
            body=cuerpo,
        )

        # Enviar el mensaje utilizando la API de Nylas
        #send_message_request = SendMessageRequest(  #Eliminado ya que no se usa esta clase
        #    draft=create_request
        #)

        nylas_client.drafts.create(create_request).send() #Envia directamente el borrador

        st.success(f"Correo electrónico enviado a {destinatario} a través de Nylas")

    except Exception as e:
        st.error(f"Error al enviar el correo electrónico con Nylas: {e}")

# Función para enviar un mensaje
def enviar_mensaje(remitente, destinatario, producto, mensaje):
    if not os.path.exists('mensajes.csv'):
        with open('mensajes.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['fecha', 'remitente', 'destinatario', 'producto', 'mensaje'])
    
    with open('mensajes.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), remitente, destinatario, producto, mensaje])

    # Enviar correo electrónico
    asunto = f"Nuevo mensaje sobre {producto} en Wallacore"
    cuerpo = f"Hola,\n\nHas recibido un nuevo mensaje de {remitente} sobre el producto {producto}:\n\n{mensaje}\n\nInicia sesión en Wallacore para responder."
    enviar_correo(destinatario, asunto, cuerpo)

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
            #st.experimental_rerun()
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
                st.success("Mensaje enviado con éxito")
                st.session_state.producto_seleccionado = None
                st.session_state.vendedor_seleccionado = None
                st.session_state.correo_vendedor = None
                #st.experimental_rerun()
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
        foto = st.text_input("URL de la foto")
        precio = st.number_input("Precio (€)", min_value=0.0, step=0.01)
        if st.button("Publicar producto"):
            añadir_producto(st.session_state.usuario, st.session_state.correo, producto, descripcion, foto, precio)
            st.success("Producto añadido con éxito")

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
                            #st.experimental_rerun()
                            st.rerun()
                        if col2.button(f"Responder mensaje {index}"):
                            st.session_state.respondiendo_mensaje = index
                            st.session_state.destinatario_respuesta = mensaje[1]
                            st.session_state.producto_respuesta = mensaje[3]
                            #st.experimental_rerun()
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
                    #st.experimental_rerun()
                    st.rerun()

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.usuario = None
        st.session_state.correo = None
        st.session_state.producto_seleccionado = None
        st.session_state.vendedor_seleccionado = None
        st.session_state.correo_vendedor = None
        #st.experimental_rerun()
        st.rerun()
