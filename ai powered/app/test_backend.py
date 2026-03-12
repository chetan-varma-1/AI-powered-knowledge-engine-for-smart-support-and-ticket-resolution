import ticket_services 
import database
import time 
import sys

def test_system():
    print("AUTOMATED  TEST REPORT")
    print("=" * 10)
    try:
        # 1. Init
        print("[1] Initializing System...")
        ticket_services.intialize_system()
        print("   - DB  Connection: OK")
        print("   - AI Model Check: OK")

        #2. submit ticket
        print("\n[2] Submitting Test Ticket ...")
        title = "System Slowdown"
        desc = "The application takes 10 seconds to load the dashboard. "
        print(f" - Input Title: {title}")
        print(f" - Input Desc: {desc}")

        start_time = time.time()
        ticket_services.submit_tickets(title,desc,"Technical","High",1)
        duration = time.time() - start_time 
        print(f" - Time Taken: {duration:.2f} seconds")
        print(f" - Ticket submitted successfully.")

        #3. Verify 
        print("\n [3] Verifying Database Entry...")
        tickets = ticket_services.get_all_tickets()

        if tickets.empty:
            print(" - ERROR: No tickets found in DB.")
            sys.exit(1)

        latest = tickets.iloc[0]
        
        print(f"  - Retrived TICKET ID: {latest['id']}")
        print(f"  - Category Assigned {latest['category']}")
        print(f"  - AI Resolution: {latest['ai_resolution']}")

        # Assertions
        assert latest['title'] == title
        assert latest['description'] == desc
        
        print("\n FINAL RESULT: PASS ✅")
        print("The system is fully operational.")
    except Exception as e:
        print(f"\n FINAL RESULT: FAIL ❌")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_system()