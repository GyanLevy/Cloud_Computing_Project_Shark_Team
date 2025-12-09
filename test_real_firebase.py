from auth_service import register_user, login_user, update_user_score, get_leaderboard

# ==========================================
# TEST CONFIGURATION
# ==========================================
test_username = "Carmel1998"
test_display_name = "Carmel Peretz"
test_password = "SecurePassword1!"
test_email = "carmel@shark-project.com"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def print_header(text):
    print("\n" + "="*60)
    print(f"   {text}")
    print("="*60)

print_header("STARTING SYSTEM TEST: AUTH & GAMIFICATION")

# ---------------------------------------------------------
# SECTION 1: VALIDATION TESTS (NEGATIVE TESTING)
# Goal: Ensure the system blocks invalid inputs.
# ---------------------------------------------------------
print("\n--- 1. Testing Input Validations (Expect Errors) ---")

# Test 1: Register with empty fields
success, msg = register_user("", "", "", "")
print(f"[Test: Empty Fields] -> {msg}") 
# Expected: Error: All fields are required.

# Test 2: Register with spaces in username
success, msg = register_user("Carmel P", "Carmel Peretz", "123456", "email@test.com")
print(f"[Test: Spaces in Username] -> {msg}")
# Expected: Error: Username cannot contain spaces...

# Test 3: Register with a weak password (too short)
success, msg = register_user("CarmelTest", "Carmel Peretz", "123", "email@test.com")
print(f"[Test: Weak Password] -> {msg}")
# Expected: Error: Password must be at least 6 characters long.


# ---------------------------------------------------------
# SECTION 2: REGISTRATION (POSITIVE TESTING)
# Goal: Create a valid user in the cloud database.
# ---------------------------------------------------------
print("\n--- 2. Testing Valid Registration ---")

success, msg = register_user(test_username, test_display_name, test_password, test_email)
print(f"[Registration Result] -> {msg}")


# ---------------------------------------------------------
# SECTION 3: LOGIN FAILURES (NEGATIVE TESTING)
# Goal: Verify that the system blocks unauthorized access.
# ---------------------------------------------------------
print("\n--- 3. Testing Login Failures (Expect Errors) ---")

# Test A: Wrong Password
# We try to login with the correct username but WRONG password
success, result = login_user(test_username, "WrongPassword123")
if not success:
    print(f"[Test: Wrong Password] -> BLOCKED SUCCESSFULLY. Msg: {result}")
else:
    print(f"[Test: Wrong Password] -> FAILED! System allowed login.")

# Test B: User Not Found
# We try to login with a user that doesn't exist
success, result = login_user("Ghost_User_999", "AnyPassword")
if not success:
    print(f"[Test: Non-existent User] -> BLOCKED SUCCESSFULLY. Msg: {result}")
else:
    print(f"[Test: Non-existent User] -> FAILED! System found a ghost.")


# ---------------------------------------------------------
# SECTION 4: VALID LOGIN (POSITIVE TESTING)
# Goal: Authenticate successfully.
# ---------------------------------------------------------
print("\n--- 4. Testing Valid Login ---")

login_success, user_data = login_user(test_username, test_password)

if login_success:
    print(f"[Login Success] Welcome back, {user_data['display_name']}!")
    print(f"[Debug] Current Score: {user_data['score']}")
else:
    print(f"[Login Failed] Reason: {user_data}")


# ---------------------------------------------------------
# SECTION 5: GAMIFICATION (SCORING)
# Goal: Update user score when a task is completed.
# ---------------------------------------------------------
print("\n--- 5. Testing Gamification ---")

if login_success:
    # Scenario: User completed a daily task (+100 points)
    new_score = update_user_score(test_username, 100)
    print(f"[Action] User completed a task (+100). New Score: {new_score}")
    
    # Scenario: User watered a plant (+50 points)
    new_score = update_user_score(test_username, 50)
    print(f"[Action] User watered a plant (+50). New Score: {new_score}")
else:
    print("[Skip] Cannot test scoring because login failed.")


# ---------------------------------------------------------
# SECTION 6: LEADERBOARD
# Goal: Display top users.
# ---------------------------------------------------------
print("\n--- 6. Testing Leaderboard Display ---")

leaders = get_leaderboard()

print(f"{'RANK':<6} {'USERNAME':<20} {'SCORE':<5}")
print("-" * 35)

for i, player in enumerate(leaders):
    print(f"{i+1:<6} {player['username']:<20} {player['score']:<5}")

print("\n" + "="*50)
print("      TEST COMPLETED SUCCESSFULLY")
print("="*50)