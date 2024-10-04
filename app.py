from flask import Flask, render_template, request, redirect, url_for, flash
import pyodbc

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

        conn = get_db_connection()  # Abrimos una vez la conexión
        if conn:
            try:
                cursor = conn.cursor()

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
                    return redirect(url_for('success'))
                else:
                    # Consultar el mensaje de error con la misma conexión
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

if __name__ == '__main__':
    app.run(debug=True)


    #http://127.0.0.1:5000/importar-xml