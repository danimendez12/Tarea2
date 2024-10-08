from flask import Flask, render_template, request, redirect, url_for, flash,session, jsonify
import pyodbc
from datetime import datetime, timedelta
import time


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

                """with open('/Users/danielmendez/Desktop/Tarea2/Datos.xml', 'r', encoding='utf-8') as file:
                    xml_data = file.read()

                # Ejecutar el procedimiento almacenado, pasando el XML como parámetro
                cursor.execute("EXEC dbo.ProcesarXML @XMLDoc=?", (xml_data,))
                conn.commit()"""





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
                    numero_intentos = intentos_fallidos[0] if intentos_fallidos else 0

                    cursor.execute("EXEC dbo.consultarError @IDerror = ?", (out_result,))
                    error_result = cursor.fetchone()
                    descripcion = f"Numero de intentos: {numero_intentos + 1} y codigo de error: {out_result}"

                    cursor.execute(
                        "EXEC dbo.insertarBitacora @IDTipoE = 2, @Descripcion = ?, @IdPostBY = ?, @Post = ?",
                        (descripcion, username, client_ip))

                    error_message = error_result[0] if error_result else 'Error desconocido.'



                else:
                    #Se  ejecuta cuando recibe un codigo de error 50003 o 50008
                    print("aca")
                    cursor.execute("DECLARE @NumeroIntentos INT;"
                                   "EXEC dbo.ContarIntentosFallidosLogin @Username = ?, @TiempoLimite = ?,  @NumeroIntentos = @NumeroIntentos OUTPUT;"
                                   "SELECT @NumeroIntentos AS NumeroIntentos;",
                                   (username, tiempo_limite))

                    intentos_fallidos = cursor.fetchone()


                    numero_intentos = intentos_fallidos[0] if intentos_fallidos else 0


                    if numero_intentos == 5:

                        # LOGIN DESHABILITADO
                        cursor.execute(
                            "EXEC dbo.insertarBitacora @IDTipoE = 3, @Descripcion = 'Login Deshabilitado', @IdPostBY = ?, @Post = ?",
                            (username, client_ip))
                        error_message = f"Demasiados intentos fallidos. Login deshabilitado por 30 min"
                    else:
                        cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
                        error_result = cursor.fetchone()
                        error_message = error_result[0] if error_result else 'Error desconocido.'

                conn.commit()
            finally:
                conn.close()

    return render_template('login.html', error_message=error_message)  # Pasa el mensaje de error al template



@app.route('/success', methods=['GET', 'POST'])
def success():

    conn = get_db_connection()
    cursor = conn.cursor()
    user = session.get('username')

    search_query = request.form.get('search_query', '')


    if search_query:
        if search_query.isdigit():
            cursor.execute(
                "EXEC dbo.insertarBitacora @IDTipoE = 12, @Descripcion = ?, @IdPostBY = ?, @Post = ?",
                (f"Búsqueda por documento: {search_query}",user, request.remote_addr))

            cursor.execute('EXEC buscarDocumento @NumeroDocumento = ?', (search_query,))

        else:
            cursor.execute(
                "EXEC dbo.insertarBitacora @IDTipoE = 11, @Descripcion = ?, @IdPostBY = ?, @Post = ?",
                (f"Búsqueda por nombre: {search_query}", user, request.remote_addr))
            cursor.execute('EXEC buscarEmpleados @Caracter = ?', (search_query,))
    else:

        cursor.execute('EXEC ListarOrdenado')


    data = cursor.fetchall()

    cursor.execute('EXEC dbo.ListarPuestos')
    puestos = cursor.fetchall()

    cursor.execute('EXEC dbo.ListarMovimientos')
    movimientos = cursor.fetchall()

    conn.commit()
    cursor.close()
    conn.close()

    return render_template('table.html', data=data, search_query=search_query, puestos=puestos,movimientos=movimientos)


@app.route('/insertar_empleado', methods=['POST'])
def insertar_empleado():

    id_puesto = request.form['id_puesto']
    doc_id = request.form['doc_id']
    nombre = request.form['nombre']
    user = session.get('username')


    fecha_contratacion = datetime.now().date()
    saldo_vacaciones = 0.0
    es_activo = 1


    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("DECLARE @NombrePuesto NVARCHAR(128); EXEC dbo.ConsultaPuesto @IdPuesto = ?, @NombrePuesto = @NombrePuesto OUTPUT; SELECT @NombrePuesto;",
                       (id_puesto,))
        nombre_puesto = cursor.fetchone()[0]

        cursor.execute(
            "DECLARE @OutResult INT; "
            "EXEC dbo.insertarEmpleado @IDpuesto = ?, @DocID = ?, @Nombre = ?, @FechaC = ?, @Saldo = ?, @EsActivo = ?,@username =?, @outresult = @OutResult OUTPUT; "
            "SELECT @OutResult AS OutResult;",
            (id_puesto, doc_id, nombre, fecha_contratacion, saldo_vacaciones, es_activo,user)
        )


        result = cursor.fetchone()
        out_result = result[0] if result else None


        if out_result == 0:
            desc_exitosa = f"Doc. Identidad: {doc_id}, Nombre: {nombre}, Puesto: {nombre_puesto}"
            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 6, @Descripcion = ?, @IdPostBY = ?, @Post = ?", (desc_exitosa, user, request.remote_addr))
            flash('Empleado insertado correctamente.')
        else:
            cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
            msgError = cursor.fetchone()

            desc_no_exitosa = f"Error: {out_result}, {msgError} Doc. Identidad: {doc_id}, Nombre: {nombre}, Puesto: {nombre_puesto}"
            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = ?, @Descripcion = ?, @IdPostBY = ?, @Post = ?",(5, desc_no_exitosa, user, request.remote_addr))

            flash(f'{msgError}')

        conn.commit()

    except Exception as e:
        flash('Error al insertar empleado. Inténtalo de nuevo más tarde.')
        print(f'Error en insertar_empleado: {e}')
    finally:
        cursor.close()
        conn.close()


    return redirect(url_for('success'))

@app.route('/actualizar_empleado', methods=['POST'])
def actualizar_empleado():

    id_empleado = request.form['id_empleado']
    nuevo_nombre = request.form['nuevo_nombre']
    nuevo_doc_id = request.form['nuevo_doc_id']
    nuevo_id_puesto = request.form['nuevo_id_puesto']
    user = session.get('username')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Consultar el empleado para obtener los datos requeridos
        cursor.execute('EXEC dbo.consultarEmpleado @EmpleadoID = ?, @username = ?', (id_empleado, user))
        empleado = cursor.fetchone()

        # Verificar que el empleado fue encontrado
        if not empleado:
            flash('Empleado no encontrado.')
            return redirect(url_for('success'))

        # Asignar variables de empleado
        nombre_empleado = empleado[1]
        puesto_empleado = empleado[2]
        saldo_vacaciones = empleado[3]

        # Actualizar el empleado
        cursor.execute(
            "DECLARE @OutResult INT; EXEC dbo.actualizarEmpleado @IdEmpleado = ?, @NuevoNombre = ?, @NuevoDocID = ?, @NuevoIDPuesto = ?, @username = ?, @outresult = @OutResult OUTPUT; SELECT @OutResult AS OutResult;",
            (id_empleado, nuevo_nombre, nuevo_doc_id, nuevo_id_puesto, user)
        )
        result = cursor.fetchone()
        out_result = result[0] if result else None
        cursor.execute(
            "DECLARE @NombrePuesto NVARCHAR(128); EXEC dbo.ConsultaPuesto @IdPuesto = ?, @NombrePuesto = @NombrePuesto OUTPUT; SELECT @NombrePuesto;",
            (nuevo_id_puesto,))
        nombre_puesto = cursor.fetchone()[0]

        # Construir la descripción
        if out_result == 0:
            DESCRIPCION = (
                f'Documento empleado: {id_empleado}, '
                f'Nombre: {nombre_empleado}, '
                f'Puesto: {puesto_empleado}, '
                f'Nuevo Nombre: {nuevo_nombre}, '
                f'Nuevo Documento de Identidad: {nuevo_doc_id}, '
                f'Nombre del Puesto: {nombre_puesto}, '
                f'Saldo de Vacaciones: {saldo_vacaciones}'
            )
            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 8, @Descripcion = ?, @IdPostBY = ?, @Post = ?", (DESCRIPCION, user, request.remote_addr))
            flash('Empleado actualizado.')
        else:
            cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
            error_result = cursor.fetchone()
            DESCRIPCION = (
                f'Error: {error_result}, '
                f'Documento empleado: {id_empleado}, '
                f'Nombre: {nombre_empleado}, '
                f'Nuevo Nombre: {nuevo_nombre}, '
                f'Nuevo Documento de Identidad: {nuevo_doc_id}, '
                f'Puesto: {puesto_empleado}, '
                f'Nombre del Puesto: {nombre_puesto}'
            )
            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = ?, @Descripcion = ?, @IdPostBY = ?, @Post = ?", (7, DESCRIPCION, user, request.remote_addr))

            error_message = error_result[0] if error_result else 'Error desconocido.'
            flash(f'Error al insertar empleado: {error_message}')

        conn.commit()

    except Exception as e:
        flash('Error al actualizar empleado. Inténtalo de nuevo más tarde.')
        print(f'Error en actualizar_empleado: {e}')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('success'))


@app.route('/eliminar_empleado', methods=['POST'])
def eliminar_empleado():


    id_empleado = request.form['id_empleado']
    doc_id = request.form['doc_id']
    user = session.get('username')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('EXEC dbo.consultarEmpleado @EmpleadoID = ?, @username = ?', (id_empleado, user))
    empleado = cursor.fetchone()
    nombre_empleado = empleado[1]
    puesto_empleado = empleado[2]
    saldo_vacaciones = empleado[3]




    try:
        descripcion = (
            f'Documento empleado: {id_empleado}, '
            f'Nombre: {nombre_empleado}, '
            f'Puesto: {puesto_empleado}, '
            f'Saldo de vacaciones: {saldo_vacaciones}, '
            f'Usuario: {user}'
        )
        cursor.execute("DECLARE @OutResult INT; EXEC dbo.eliminarEmpleado @IdEmpleado = ?, @DocId = ?, @username = ?, @outresult = @OutResult OUTPUT; SELECT @OutResult AS OutResult;", (id_empleado, doc_id, user))

        result = cursor.fetchone()
        out_result = result[0] if result else None

        if out_result == 0:

            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 10, @Descripcion = ?, @IdPostBY = ?, @Post = ?", (descripcion,user, request.remote_addr))
            flash('Empleado eliminado.')
        else:

            cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 9, @Descripcion = ?, @IdPostBY = ?, @Post = ?", (descripcion,user, request.remote_addr))
            cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
            error_result = cursor.fetchone()
            error_message = error_result[0] if error_result else 'Error desconocido.'
            flash(f'Error al eliminar empleado: {error_message}')

        conn.commit()

    except Exception as e:
        flash('Error al eliminar empleado. Inténtalo de nuevo más tarde.')
        print(f'Error en eliminar_empleado: {e}')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('success'))

@app.route('/movimientos/<documento_id>', methods=['GET'])
def movimientos(documento_id):


    conn = get_db_connection()
    cursor = conn.cursor()

    # Ejecutar el procedimiento almacenado para obtener movimientos por documento
    start_time = time.time()
    cursor.execute('EXEC ObtenerMovimientos @IdEmpleado = ?', (documento_id,))
    movimientos = cursor.fetchall()
    end_time = time.time()
    execution_time = end_time - start_time
    print(f'Tiempo de ejecución de la función: {execution_time:.2f} segundos')

    cursor.close()
    conn.close()

    # Pasar los movimientos a la plantilla
    return render_template('movimientos.html', movimientos=movimientos, documento_id=documento_id)

@app.route('/insertar_movimiento', methods=['POST'])
def insertar_movimiento():

    id_empleado = request.form['id_empleado']
    id_tipo_mov = request.form['id_tipo_mov']
    monto = abs(float(request.form['monto']))
    user = session.get('username')
    ip = request.remote_addr
    fecha = datetime.now().date()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('EXEC dbo.consultarEmpleado @EmpleadoID = ?, @username = ?', (id_empleado, user))
    empleado = cursor.fetchone()
    nombre_empleado = empleado[1]
    puesto_empleado = empleado[2]
    saldo_vacaciones = empleado[3]



    cursor.execute(
        "DECLARE @OutResult INT; "
        "EXEC dbo.insertarMovimiento @IdEmpleado = ?, @IdTipoMov = ?, @Fecha = ?, @Monto = ?, @IdUser = ?, @IP = ?,@Saldo = ? ,@outresult = @OutResult OUTPUT; "
        "SELECT @OutResult AS OutResult;",
        (id_empleado, id_tipo_mov, fecha, monto, user, ip,saldo_vacaciones)
    )

    result = cursor.fetchone()
    out_result = result[0] if result else None

    cursor.execute('EXEC dbo.ConsultarMovimiento @idMovimiento = ?', (id_tipo_mov))
    movimiento = cursor.fetchone()

    if out_result == 0:
        descripcion = (
            f'Documento empleado: {id_empleado}, '
            f'Nombre: {nombre_empleado}, '
            f'Saldo de vacaciones: {saldo_vacaciones}, '
            f'Movimiento: {movimiento}, '
            f'Monto: {monto}, '
            f'Usuario: {user}'
        )
        cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 14, @Descripcion = ?, @IdPostBY = ?, @Post = ?", (descripcion,user, ip))
        flash('Movimiento insertado correctamente.')
    else:
        cursor.execute("EXEC dbo.consultarError @IDerror=?", (out_result,))
        error_result = cursor.fetchone()
        error_message = error_result[0] if error_result else 'Error desconocido.'
        descripcion = (
            f'Error: {error_result}, '
            f'Documento empleado: {id_empleado}, '
            f'Nombre: {nombre_empleado}, '
            f'Saldo de vacaciones: {saldo_vacaciones}, '
            f'Movimiento: {movimiento}, '
            f'Monto: {monto}, '
            f'Usuario: {user}'
        )
        cursor.execute("EXEC dbo.insertarBitacora @IDTipoE = 13, @Descripcion = ?, @IdPostBY = ?, @Post = ?",(descripcion,user, ip))

        flash(f'Error al insertar movimiento: {error_message}')

    conn.commit()


    return redirect(url_for('success'))


@app.route('/consultar_empleado/<documento_id>', methods=['GET'])
def consultar_empleado(documento_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    user = session.get('username')  # Obtener el nombre de usuario de la sesión

    # Ejecutar el procedimiento almacenado para obtener la información del empleado
    cursor.execute('EXEC dbo.consultarEmpleado @EmpleadoID = ?, @username = ?', documento_id, user)

    empleado = cursor.fetchall()  # Obtener todos los resultados de la consulta

    cursor.close()
    conn.close()

    # Pasar los datos del empleado a la plantilla
    return render_template('Empleado.html', empleado=empleado, documento_id=documento_id)


@app.route('/logout')
def logout():

    conn = get_db_connection()
    cursor = conn.cursor()
    client_ip = request.remote_addr
    user = session.get('username')

    try:
        cursor.execute(
            "EXEC dbo.insertarBitacora @IDTipoE = 4, @Descripcion = 'Logout', @IdPostBY = ?, @Post = ?",
            (user, client_ip))
        conn.commit()
        flash('Has cerrado sesión con éxito.')
    except Exception as e:

        flash('Error al cerrar sesión. Inténtalo de nuevo más tarde.')
        print(f'Error en logout: {e}')
    finally:
        cursor.close()
        conn.close()


    return redirect(url_for('index'))
if __name__ == '__main__':
    app.run(debug=True)


