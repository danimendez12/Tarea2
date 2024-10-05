from flask import Flask, render_template, request, redirect, url_for, flash,session
import pyodbc
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Connection to SQL Server
def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
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


                    cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 1, @Descripcion = 'Login Exitoso', @IdPostBY = ?, @Post = ?",
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

                    # Verificar si el número de intentos fallidos es mayor a límite 5
                    if numero_intentos >= 5:

                        #LOGIN DESHABILITADO
                        cursor.execute(
                            "EXEC dbo.insertarBitacora @IDTipoE = 3, @Descripcion = 'Login Deshabilitado', @IdPostBY = ?, @Post = ?",
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

    cursor.execute('EXEC dbo.ListarPuestos')
    puestos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('table.html', data=data, search_query=search_query, puestos=puestos)


@app.route('/insertar_empleado', methods=['POST'])
def insertar_empleado():

    id_puesto = request.form['id_puesto']
    doc_id = request.form['doc_id']
    nombre = request.form['nombre']
    user = session.get('username')

    # Default para empleados nuevos
    fecha_contratacion = datetime.now().date()
    saldo_vacaciones = 0.0
    es_activo = 1


    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "DECLARE @OutResult INT; "
            "EXEC dbo.insertarEmpleado @IDpuesto = ?, @DocID = ?, @Nombre = ?, @FechaC = ?, @Saldo = ?, @EsActivo = ?, @outresult = @OutResult OUTPUT; "
            "SELECT @OutResult AS OutResult;",
            (id_puesto, doc_id, nombre, fecha_contratacion, saldo_vacaciones, es_activo)
        )


        result = cursor.fetchone()
        out_result = result[0] if result else None


        if out_result == 0:

            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 6, @Descripcion = 'Insercion exitosa', @IdPostBY = ?, @Post = ?", (user, request.remote_addr))
            flash('Empleado insertado correctamente.')
        else:

            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = ?, @Descripcion = ?, @IdPostBY = ?, @Post = ?",(5, 'Inserción no exitosa', user, request.remote_addr))

            cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
            error_result = cursor.fetchone()
            error_message = error_result[0] if error_result else 'Error desconocido.'
            flash(f'Error al insertar empleado: {error_message}')

        conn.commit()

    except Exception as e:
        flash('Error al insertar empleado. Inténtalo de nuevo más tarde.')
        print(f'Error en insertar_empleado: {e}')
    finally:
        cursor.close()
        conn.close()


    return redirect(url_for('success'))


@app.route('/logout')
def logout():
    conn = get_db_connection()
    cursor = conn.cursor()
    client_ip = request.remote_addr
    user = session.get('username')  # Asegúrate de tener una función que obtenga el usuario actual.

    try:
        cursor.execute(
            "EXEC dbo.insertarBitacora @IDTipoE = 4, @Descripcion = 'Logout', @IdPostBY = ?, @Post = ?",
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

