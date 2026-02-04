# Flask core functions for routing, templates, forms, sessions, and flash messages
from flask import Flask, render_template, request, redirect, url_for, session, flash

# For secure password hashing and verification
from werkzeug.security import generate_password_hash, check_password_hash

# For handling dates (check-in, check-out, discounts)
from datetime import datetime

# For generating secure email activation tokens
from itsdangerous import URLSafeTimedSerializer

# For sending emails (account activation)
from flask_mail import Mail, Message

# Custom database helper file (MySQL connection logic)
import dbfunc

# Create Flask application instance
app = Flask(__name__)

# Secret key used for sessions and security
app.secret_key = 'secret_key_123'

#MAIL CONFIG gmail smtp server to send email from email
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='reewani1010@gmail.com',
    MAIL_PASSWORD='adthvpzfforzigkh',
    MAIL_DEFAULT_SENDER='reewani1010@gmail.com'
)
# Initialize Flask-Mail
mail = Mail(app)

# Serializer used to create secure activation tokens
serializer = URLSafeTimedSerializer(app.secret_key)

#PRICE CALCULATION
def calculate_price_logic(peak, off, room_type, guests, check_in, check_out):
    # Determine booking month
    month = check_in.month

    # Peak season logic (Apr–Aug and Nov–Dec)
    is_peak = (4 <= month <= 8) or (month >= 11)

    # Select base rate depending on season
    base_rate = float(peak) if is_peak else float(off)

    # Default values
    multiplier = 1.0
    surcharge = 0.0

    # Adjust pricing based on room type and guests
    if room_type == 'Double':
        multiplier = 1.2
        if guests == 2:
            surcharge = base_rate * 0.10
    elif room_type == 'Family':
        multiplier = 1.5

    # Final nightly rate
    nightly_rate = (base_rate * multiplier) + surcharge

    # Ensures the minimum as 1 night
    nights = max((check_out - check_in).days, 1)

    # Total before discount
    gross = nightly_rate * nights

    # Early booking discount logic
    days_advance = (check_in - datetime.now().date()).days
    discount_pct = 0

    if 80 <= days_advance <= 90:
        discount_pct = 0.30
    elif 60 <= days_advance <= 79:
        discount_pct = 0.20
    elif 45 <= days_advance <= 59:
        discount_pct = 0.10

    # Calculate discount and final price
    discount = gross * discount_pct
    final_price = gross - discount

    # Return rounded values
    return round(final_price, 2), round(discount, 2), is_peak


#------HOME PAGE------
@app.route('/')
def index():
    #connecting to database
    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)
    # Fetch all hotels sorted by city
    cursor.execute("SELECT * FROM hotels ORDER BY city")
    hotels = cursor.fetchall()

    conn.close()

    # Render homepage with hotel data
    return render_template("index.html", hotels=hotels)

#------ REGISTER ------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        #getting user input
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = dbfunc.getConnection()
        cursor = conn.cursor(dictionary=True)
        # To Prevent duplicate username/email
        cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
        if cursor.fetchone():
            flash("Username or email already exists.", "error")
            conn.close()
            return redirect(url_for('register'))

        # Hash password before saving it
        hashed = generate_password_hash(password)

        # Inserting new user (inactive=default)
        cursor.execute(
            "INSERT INTO users (username, password, email, status, role) VALUES (%s,%s,%s,0,'user')",
            (username, hashed, email)
        )
        conn.commit()
        conn.close()

        # Generating activation token
        token = serializer.dumps(email, salt='email-confirm')
        link = url_for('activate', token=token, _external=True)

        # Sending activation email
        msg = Message("Activate Your Account", recipients=[email])
        msg.body = f"Hi {username},\n\nActivate your account:\n{link}"
        mail.send(msg)

        flash("Check your email to activate your account.", "success")
        return redirect(url_for('login'))

    return render_template("register.html")

#------ ACTIVATE ------
@app.route('/activate/<token>')
def activate(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        flash("Activation link expired.", "error")
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status=1 WHERE email=%s", (email,))
    conn.commit()
    conn.close()

    flash("Account activated successfully!", "success")
    return redirect(url_for('login'))

#------ LOGIN ------
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = dbfunc.getConnection()
        cursor = conn.cursor(dictionary=True)
        # Fetching the  user record
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()

        #checking authetication
        if not user or not check_password_hash(user['password'], password):
            msg = "Invalid username or password."
        elif user['status'] == 0:
            msg = "Account not activated."
        else:
            #storing login sessions
            session.update({
                'loggedin': True,
                'id': user['id'],
                'role': user['role'],
                'username': user['username']
            })
            return redirect(url_for('admin_dashboard' if user['role'] == 'admin' else 'user_dashboard'))

    return render_template("login.html", msg=msg)

#------ LOGOUT ------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#------ SEARCH ------
@app.route('/search', methods=['POST'])
def search():
    hotel_id = request.form.get('hotel_id')
    guests = int(request.form.get('guests', 1))
    check_in_str = request.form.get('check_in')
    check_out_str = request.form.get('check_out')

    room_type = 'Standard'
    if guests == 2: room_type = 'Double'
    elif guests > 2: room_type = 'Family'

    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)

    # We always fetch hotel info so the template has data to show
    cursor.execute("SELECT * FROM hotels WHERE id=%s", (hotel_id,))
    hotel = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM rooms 
        WHERE hotel_id=%s AND type_name=%s AND status='Available' 
        LIMIT 1
    """, (hotel_id, room_type))
    room = cursor.fetchone()

    results = None
    # Only build the results dictionary if BOTH hotel and room are found
    if hotel and room:
        try:
            # Parse dates safely
            date_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            date_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
            
            price, discount, _ = calculate_price_logic(
                hotel['peak_rate'], hotel['off_peak_rate'],
                room_type, guests, date_in, date_out
            )

            results = {
                'hotel': hotel,
                'room': room,
                'price': price,
                'discount': discount,
                'guests': guests,
                'dates': {'in': check_in_str, 'out': check_out_str}
            }
        except Exception as e:
            print(f"Calculation Error: {e}")

    conn.close()
    # Send results (which might be None). 
    # results.html MUST have {% if results %} at the top to handle None.
    return render_template("results.html", results=results)

#------ BOOKINGS (PENDING) -------
@app.route('/book', methods=['POST'])
def book():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bookings
        (user_id, room_id, check_in, check_out, guest_count, total_price, discount_amount, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'Pending')
    """, (
        session['id'],
        int(request.form['room_id']),
        request.form['check_in'],
        request.form['check_out'],
        int(request.form['guests']),
        float(request.form['total_price']),
        float(request.form['discount'])
    ))

    cursor.execute("UPDATE rooms SET status='Booked' WHERE id=%s", (request.form['room_id'],))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()

    return redirect(url_for('receipt', id=booking_id))

#------ ADMIN DASHBOARD ------
@app.route('/admin/dashboard')
def admin_dashboard():
    # Security check, Only admins allowed
    if 'loggedin' not in session or session.get('role') != 'admin':
        flash("Unauthorized access.", "error")
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)

    # 1. Calculating Total Revenue
    cursor.execute("""
        SELECT SUM(total_price - discount_amount) as total 
        FROM bookings 
        WHERE status IN ('Confirmed', 'Paid')
    """)
    total_sales = cursor.fetchone()['total'] or 0

    # 2. Getting Hotel Statsas in Revenue per hotel
    cursor.execute("""
        SELECT h.*, 
        SUM(CASE WHEN b.status IN ('Confirmed', 'Paid') THEN (b.total_price - b.discount_amount) ELSE 0 END) as revenue
        FROM hotels h
        LEFT JOIN rooms r ON h.id = r.hotel_id
        LEFT JOIN bookings b ON r.id = b.room_id
        GROUP BY h.id
    """)
    hotel_stats = cursor.fetchall()
    
    # Calculating the simulated profit 
    for h in hotel_stats:
        rev = float(h['revenue'] or 0)
        h['profit'] = round(rev * 0.40, 2)

    # 3. Monthly Sales Report 
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%M %Y') as month, 
        SUM(total_price - discount_amount) as revenue
        FROM bookings
        WHERE status IN ('Confirmed', 'Paid')
        GROUP BY month 
        ORDER BY MIN(created_at) DESC
    """)
    monthly_sales = cursor.fetchall()

    # 4. Top Customers
    cursor.execute("""
        SELECT u.username, SUM(b.total_price - b.discount_amount) as spent
        FROM users u
        JOIN bookings b ON u.id = b.user_id
        WHERE b.status IN ('Confirmed', 'Paid')
        GROUP BY u.id 
        ORDER BY spent DESC LIMIT 5
    """)
    top_customers = cursor.fetchall()

    # 5. Listing users for password change dropdown
    cursor.execute("SELECT username FROM users WHERE role='user'")
    all_users = cursor.fetchall()

    conn.close()
    
    return render_template("admin_dashboard.html", 
                           total_sales=round(total_sales, 2),
                           hotel_stats=hotel_stats,
                           monthly_sales=monthly_sales,
                           top_customers=top_customers,
                           users=all_users)

@app.route('/admin/add_hotel', methods=['POST'])
def add_hotel():
    if session.get('role') != 'admin': return redirect('/')
    city = request.form['city']
    peak = request.form['peak']
    off = request.form['off']
    
    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO hotels (city, peak_rate, off_peak_rate) VALUES (%s, %s, %s)", (city, peak, off))
    conn.commit()
    conn.close()
    flash(f"New branch in {city} added!", "success")
    return redirect(url_for('admin_dashboard'))

#------ ADMIN, UPDATE HOTEL PRICES ------
@app.route('/admin/update_price', methods=['POST'])
def update_price():
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    hotel_id = request.form['hotel_id']
    peak = request.form['peak_rate']
    off = request.form['off_peak_rate']

    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE hotels 
        SET peak_rate=%s, off_peak_rate=%s 
        WHERE id=%s
    """, (peak, off, hotel_id))
    conn.commit()
    conn.close()

    flash("Hotel rates updated successfully!", "success")
    return redirect(url_for('admin_dashboard'))

#------ ADMIN, CHANGE USER PASSWORD ------
@app.route('/admin/change_password', methods=['POST'])
def admin_change_password():
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    target_user = request.form['username']
    new_password = generate_password_hash(request.form['new_password'])

    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password=%s WHERE username=%s", (new_password, target_user))
    conn.commit()
    conn.close()

    flash(f"Password for {target_user} has been reset.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_room/<int:room_id>')
def toggle_room(room_id):
    if session.get('role') != 'admin': return redirect('/')
    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT status FROM rooms WHERE id=%s", (room_id,))
    res = cursor.fetchone()
    new_status = 'Booked' if res['status'] == 'Available' else 'Available'
    
    cursor.execute("UPDATE rooms SET status=%s WHERE id=%s", (new_status, room_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

#------ ADMIN, DELETE HOTELS ------
@app.route('/admin/delete_hotel/<int:id>')
def delete_hotel(id):
    if session.get('role') != 'admin': return redirect('/')
    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    # Delete rooms first due to foreign key constraints
    cursor.execute("DELETE FROM rooms WHERE hotel_id=%s", (id,))
    cursor.execute("DELETE FROM hotels WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    flash("Hotel and associated rooms removed.", "success")
    return redirect(url_for('admin_dashboard'))

#------ ADMIN, DELETE USER ------
@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if session.get('role') != 'admin': return redirect('/')
    
    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    
    
    cursor.execute("DELETE FROM bookings WHERE user_id=%s", (user_id,))
    
    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User account and details removed from system.", "success")
    return redirect(url_for('admin_dashboard'))

#------ ADMIN, MANAGING ROOMS ------
@app.route('/admin/manage_rooms/<int:hotel_id>')
def manage_rooms(hotel_id):
    if session.get('role') != 'admin': return redirect('/')
    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rooms WHERE hotel_id=%s", (hotel_id,))
    rooms = cursor.fetchall()
    conn.close()
    return render_template("admin_rooms.html", rooms=rooms)
 
#------ ADMIN, UPDATING EXCHANGE RATE ------
@app.route('/admin/update_exchange', methods=['POST'])
def update_exchange():
    if session.get('role') != 'admin': return redirect('/')
    usd = request.form['usd_rate']
    eur = request.form['eur_rate']
    
    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    if usd:
        cursor.execute("UPDATE exchange_rates SET rate_to_gbp=%s WHERE currency_code='USD'", (usd,))
    if eur:
        cursor.execute("UPDATE exchange_rates SET rate_to_gbp=%s WHERE currency_code='EUR'", (eur,))
    conn.commit()
    conn.close()
    flash("Exchange rates updated.", "success")
    return redirect(url_for('admin_dashboard'))

#------ USER DASHBOARD ------
@app.route('/user/dashboard')
def user_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.*, h.city, r.type_name, r.room_number
        FROM bookings b
        JOIN rooms r ON b.room_id=r.id
        JOIN hotels h ON r.hotel_id=h.id
        WHERE b.user_id=%s
        ORDER BY b.created_at DESC
    """, (session['id'],))
    bookings = cursor.fetchall()
    conn.close()

    return render_template("user_dashboard.html", bookings=bookings)

#------ USER, CHANGE PASSWORD ------
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    msg = ""
    success = False

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        conn = dbfunc.getConnection()
        cursor = conn.cursor(dictionary=True)

        # Fetch user
        cursor.execute("SELECT * FROM users WHERE id=%s", (session['id'],))
        user = cursor.fetchone()

        if not user or not check_password_hash(user['password'], old_password):
            msg = "Current password is incorrect."
        else:
            # Update password
            hashed = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, session['id']))
            conn.commit()
            msg = "Password updated successfully!"
            success = True

        cursor.close()
        conn.close()

    return render_template('change_password.html', msg=msg, success=success)


#------ USER, CHANGE EMAIL ------
@app.route('/change_email', methods=['GET', 'POST'])
def change_email():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    msg = ""
    success = False

    if request.method == 'POST':
        new_email = request.form['email']

        conn = dbfunc.getConnection()
        cursor = conn.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email=%s AND id!=%s", (new_email, session['id']))
        if cursor.fetchone():
            msg = "Email is already in use."
        else:
            cursor.execute("UPDATE users SET email=%s WHERE id=%s", (new_email, session['id']))
            conn.commit()
            session['email'] = new_email
            msg = "Email updated successfully!"
            success = True

        cursor.close()
        conn.close()

    return render_template('change_email.html', msg=msg, success=success)

#------ CHANGING PROFILE ------
@app.route('/change_profile', methods=['GET', 'POST'])
def change_profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    msg = ""
    success = False

    if request.method == 'POST':
        email = request.form['email']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        conn = dbfunc.getConnection()
        cursor = conn.cursor(dictionary=True)
        
        # Verify old password
        cursor.execute("SELECT * FROM users WHERE id=%s", (session['id'],))
        user = cursor.fetchone()
        if not user or not check_password_hash(user['password'], old_password):
            msg = "Current password is incorrect."
        else:
            # Check if email is used by another user
            cursor.execute("SELECT * FROM users WHERE email=%s AND id!=%s", (email, session['id']))
            if cursor.fetchone():
                msg = "Email is already in use."
            else:
                hashed = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET email=%s, password=%s WHERE id=%s",
                               (email, hashed, session['id']))
                conn.commit()
                session['email'] = email
                msg = "Profile updated successfully!"
                success = True
        
        cursor.close()
        conn.close()

    return render_template('change_profile.html', msg=msg, success=success)


#------ CANCELLING BOOKING ------
@app.route('/booking/cancel/<int:id>')
def cancel(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookings SET status='Cancelled' WHERE id=%s AND user_id=%s",
        (id, session['id'])
    )
    conn.commit()
    conn.close()

    flash("Booking cancelled successfully.", "success")
    return redirect(url_for('user_dashboard'))

#------ CHECKOUT SIMULATION ------
@app.route('/checkout/<int:id>')
def checkout(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM bookings WHERE id = %s AND user_id = %s", (id, session['id']))
    booking = cursor.fetchone()
    conn.close()

    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for('user_dashboard'))

    return render_template("checkout.html", booking=booking)

#------- PAY PROCESS ------
@app.route('/pay/<int:id>', methods=['POST'])
def pay(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor()

    # We update status to 'Paid' instead of 'Confirmed'
    cursor.execute("""
        UPDATE bookings
        SET status='Paid'
        WHERE id=%s AND user_id=%s
    """, (id, session['id']))

    conn.commit()
    conn.close()

    flash("Payment successful! Your stay is now guaranteed.", "success")
    return redirect(url_for('receipt', id=id))

#------- RECEIPT -------
@app.route('/receipt/<int:id>')
def receipt(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT b.*, r.room_number, r.type_name, h.city
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN hotels h ON r.hotel_id = h.id
        WHERE b.id = %s AND b.user_id = %s
    """, (id, session['id']))

    booking = cursor.fetchone()
    conn.close()

    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for('user_dashboard'))

    return render_template("receipt.html", booking=booking)

#------ MONEY ------
@app.template_filter('money')
def money(value):
    """
    Formats numbers to two decimal places for currency display
    Prevents floating-point precision issues
    """
    try:
        return f"{float(value):.2f}"
    except:
        return "0.00"

# ---------------- SEED ROOMS LOGIC ----------------
@app.route('/seed_rooms')
def seed_rooms():
    if session.get('role') != 'admin':
        return redirect('/')

    conn = dbfunc.getConnection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all hotels to generate rooms for each branch
    cursor.execute("SELECT id, city, total_capacity FROM hotels")
    hotels = cursor.fetchall()

    for hotel in hotels:
        h_id = hotel['id']
        cap = hotel['total_capacity']

        # Calculate counts based on 30/50/20 ratio
        std_count = int(cap * 0.30)
        dbl_count = int(cap * 0.50)
        fam_count = cap - std_count - dbl_count # Remaining balance

        # Check if rooms already exist to prevent duplicates
        cursor.execute("SELECT COUNT(*) as count FROM rooms WHERE hotel_id=%s", (h_id,))
        if cursor.fetchone()['count'] > 0:
            continue

        # Insert Standard Rooms (S1, S2...)
        for i in range(1, std_count + 1):
            cursor.execute("INSERT INTO rooms (hotel_id, room_number, type_name, status) VALUES (%s, %s, 'Standard', 'Available')", (h_id, f"S{i}"))

        # Insert Double Rooms (D1, D2...)
        for i in range(1, dbl_count + 1):
            cursor.execute("INSERT INTO rooms (hotel_id, room_number, type_name, status) VALUES (%s, %s, 'Double', 'Available')", (h_id, f"D{i}"))

        # Insert Family Rooms (F1, F2...)
        for i in range(1, fam_count + 1):
            cursor.execute("INSERT INTO rooms (hotel_id, room_number, type_name, status) VALUES (%s, %s, 'Family', 'Available')", (h_id, f"F{i}"))

    conn.commit()
    conn.close()
    flash("Room inventory generated successfully (30% Std / 50% Dbl / 20% Fam).", "success")
    return redirect(url_for('admin_dashboard'))

#------ RUN ------
# Run the Flask application in debug mode
if __name__ == '__main__':
    app.run(debug=True)

# Print all registered routes (useful for debugging)
print(app.url_map)

