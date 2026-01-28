
def check_key(filename, key):
    with open(filename, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
    
    if key in lines:
        print(f"Key '{key}' FOUND in {filename}")
        return True
    else:
        print(f"Key '{key}' NOT FOUND in {filename}")
        # Fuzzy check
        match = [l for l in lines if key in l]
        if match:
            print(f"   But found similar keys: {match[:5]}")
        return False

k = '4458837'
print(f"Checking {k}...")
in_err = check_key("keys_dump_errors.txt", k)
in_base = check_key("keys_dump_base.txt", k)

if in_err and in_base:
    print("BOTH have the key. Merge SHOULD have worked.")
else:
    print("Key missing in one side.")
