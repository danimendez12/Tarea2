from flask import Flask, render_template, request, redirect, url_for, flash
import xml.etree.ElementTree as ET
import pyodbc

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for using flash messages

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

def leer_xml():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Load and parse the XML file
        tree = ET.parse('Datos.xml')  # Ensure the correct XML file name
        root = tree.getroot()

        # Process the Puestos section
        for puesto in root.find('Puestos'):
            nombre = puesto.get('Nombre')
            salario = puesto.get('SalarioxHora')

            # Insert into the Puesto table
            cursor.execute("EXEC dbo.InsertarPuesto @Nombre=?, @SalarioxHora=?", (nombre, salario))

        # Commit changes after all inserts
        conn.commit()
        print("Datos de puestos insertados correctamente.")

    except Exception as e:
        # Handle any errors and roll back in case of failure
        conn.rollback()
        print(f"Error al insertar datos de puestos: {e}")

    finally:
        # Always close the connection
        conn.close()


@app.route('/importar-xml', methods=['GET'])
def importar_xml():
    try:
        leer_xml()  # Ejecuta la función que lee el XML e inserta los datos en la base de datos
        flash('Datos importados exitosamente desde el XML.')
    except Exception as e:
        flash(f'Ocurrió un error al importar el XML: {e}')

    return redirect(url_for('index'))  # Redirige de vuelta a la página principal o a la que prefieras


# Main route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            # Prepare an output parameter
            out_result = cursor.execute("DECLARE @OutResult BIT; "
                                         "EXEC dbo.ValidarUsuario @Username=?, @Password=?, @OutResult=@OutResult OUTPUT; "
                                         "SELECT @OutResult AS OutResult;",
                                         (username, password)).fetchone()[0]

            conn.close()

            if out_result == 1:
                return redirect(url_for('success'))
            else:
                flash('Credenciales inválidas. Intenta de nuevo.')

        else:
            flash('No se pudo conectar a la base de datos.')

    return render_template('login.html')

# Route for successful authentication
@app.route('/success')
def success():
    return 'Login exitoso!'

if __name__ == '__main__':
    app.run(debug=True)


    #http://127.0.0.1:5000/importar-xml