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
            content.seek(0)
            file_data = content.read()
            response = self.client.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_data,
                file_options={"content-type": "application/pdf"}
            )
            return response.path
        except Exception as e:
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