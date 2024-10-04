from flask import Flask, render_template, request, redirect, url_for, flash,session
import pyodbc
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Connection to SQL Server
def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=mssql-180519-0.cloudclusters.net,10034;'
        'DATABASE=Base_de_datos;'
        'UID=Admin;'
        'PWD=Db12345678;'
        'Encrypt=no;'  # Disable SSL only for testing
        'TrustServerCertificate=yes;'  # Trust the server's certificate
    )
    return conn



# Main route
@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        client_ip = request.remote_addr
        tiempo_limite = datetime.now() - timedelta(minutes=30)
        numero_intentos = 0

        conn = get_db_connection()  # Abrimos una vez la conexión
        if conn:
            try:
                cursor = conn.cursor()
                """
                with open('/Users/danielmendez/Desktop/Tarea2/Datos.xml', 'r', encoding='utf-8') as file:
                    xml_data = file.read()

                # Ejecutar el procedimiento almacenado, pasando el XML como parámetro
                cursor.execute("EXEC dbo.ProcesarXML @XMLDoc=?", (xml_data,))
                conn.commit()
                """



                # Primera ejecución
                cursor.execute("DECLARE @OutResult INT;"
                               " EXEC dbo.ValidarUsuario @Username = ?, @Password = ?, @OutResult = @OutResult OUTPUT;"
                               " SELECT @OutResult AS OutResult;", (username, password))


                result = cursor.fetchone()

                if result:
                    out_result = result[0]
                else:
                    out_result = None

                if out_result == 0:
                    session['username'] = username

                    cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 1, @Descripcion = ' ', @IdPostBY = ?, @Post = ?",
                                   ( username, client_ip))

                    conn.commit()
                    return redirect(url_for('success'))
                elif out_result == 50001 or out_result == 50002 :
                    cursor.execute("DECLARE @NumeroIntentos INT;"
                                   "EXEC dbo.ContarIntentosFallidosLogin @Username = ?, @TiempoLimite = ?,  @NumeroIntentos = @NumeroIntentos OUTPUT;"
                                   "SELECT @NumeroIntentos AS NumeroIntentos;",
                                   (username, tiempo_limite))

                    intentos_fallidos = cursor.fetchone()

                    if intentos_fallidos:
                        numero_intentos = intentos_fallidos[0]

                    cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
                    error_result = cursor.fetchone()
                    descripcion = f"Numero de intentos: {numero_intentos} y codigo de error: {error_result[0]}"

                    cursor.execute(
                        "EXEC dbo.insertarBitacora @IDTipoE = 2, @Descripcion = ?, @IdPostBY = ?, @Post = ?",
                        (descripcion,username, client_ip))

                    # Verificar si el número de intentos fallidos es mayor a un límite, por ejemplo 3
                    if numero_intentos >= 5:

                        cursor.execute(
                            "EXEC dbo.insertarBitacora @IDTipoE = 3, @Descripcion = ' ', @IdPostBY = ?, @Post = ?",
                            (username, client_ip))
                        error_message = f"Demasiados intentos fallidos. Login deshabilitado por 30 min"
                    else:
                        cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
                        error_result = cursor.fetchone()
                        error_message = error_result[0] if error_result else 'Error desconocido.'
                else:
                    cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
                    error_result = cursor.fetchone()
                    error_message = error_result[0] if error_result else 'Error desconocido.'

                conn.commit()
            finally:
                conn.close()

    return render_template('login.html', error_message=error_message)  # Pasa el mensaje de error al template



@app.route('/success')
def success():

    conn = get_db_connection()
    cursor = conn.cursor()


    search_query = request.form.get('search_query', '')


    if search_query:
        cursor.execute('EXEC SearchEmployees @SearchTerm = ?', search_query)
    else:

        cursor.execute('EXEC ListarOrdenado')


    data = cursor.fetchall()


    cursor.close()
    conn.close()


    return render_template('table.html', data=data, search_query=search_query)


@app.route('/logout')
def logout():
    conn = get_db_connection()
    cursor = conn.cursor()
    client_ip = request.remote_addr
    user = session.get('username')  # Asegúrate de tener una función que obtenga el usuario actual.

    try:
        cursor.execute(
            "EXEC dbo.insertarBitacora @IDTipoE = 4, @Descripcion = ' ', @IdPostBY = ?, @Post = ?",
            (user, client_ip))
        conn.commit()
        flash('Has cerrado sesión con éxito.')  # Mensaje de confirmación
    except Exception as e:
        # Manejo de errores: puedes registrar el error o mostrar un mensaje al usuario
        flash('Error al cerrar sesión. Inténtalo de nuevo más tarde.')  # Mensaje de error
        print(f'Error en logout: {e}')  # Registro del error en la consola o en un archivo de log
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))
if __name__ == '__main__':
    app.run(debug=True)

