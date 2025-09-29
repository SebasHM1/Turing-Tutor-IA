# turing/storage_backends.py

import os
from django.core.files.storage import Storage
from supabase import create_client, Client
from django.conf import settings
from io import BytesIO

class SupabaseStorage(Storage):
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.bucket_name = os.environ.get("SUPABASE_BUCKET_NAME")
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

    def _save(self, name, content):
        """
        Guarda el archivo en el bucket de Supabase.
        'name' es el nombre/ruta del archivo.
        'content' es el archivo en sí.
        """
        try:
            print(f"DEBUG: Attempting to save file: {name}")
            # Nos aseguramos de que el content se pueda leer varias veces si es necesario
            content.seek(0)
            file_data = content.read()
            print(f"DEBUG: File size: {len(file_data)} bytes")
            
            # Usamos la librería de Supabase para subir el archivo
            response = self.client.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_data,
                # 'content-type' es importante para que el navegador sepa cómo mostrar el PDF
                file_options={"content-type": "application/pdf"} 
            )
            print(f"DEBUG: Supabase upload response: {response}")
            
            # Devolvemos el nombre del archivo para que Django lo guarde en la base de datos
            return name
        except Exception as e:
            print(f"DEBUG: Error saving file to Supabase: {str(e)}")
            raise e

    def url(self, name):
        """
        Devuelve la URL pública del archivo.
        'name' es el nombre/ruta del archivo guardado en la BBDD.
        """
        return self.client.storage.from_(self.bucket_name).get_public_url(name)

    def delete(self, name):
        """
        Elimina el archivo del bucket.
        """
        self.client.storage.from_(self.bucket_name).remove([name])
    
    def exists(self, name):
        """
        Comprueba si un archivo existe. Esto es más complejo con Supabase,
        así que por ahora devolvemos False para forzar la subida,
        o puedes implementar una lógica de listado si es necesario.
        """
        # Esta es una simplificación. Una implementación real podría listar
        # los archivos en el directorio para ver si 'name' está en la lista.
        return False

    def _open(self, name, mode='rb'):
        """
        Abre el archivo para leerlo.
        """
        response = self.client.storage.from_(self.bucket_name).download(name)
        return BytesIO(response)