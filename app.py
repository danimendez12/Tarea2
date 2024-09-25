from flask import Flask, render_template, request, redirect, url_for, flash
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

# Main route
# Main route
# Main route
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