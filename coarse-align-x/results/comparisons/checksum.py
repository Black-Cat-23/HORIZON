def ones_complement_add(a, b):
    total = int(a, 2) + int(b, 2)

    while total > 15:
        carry = total >> 4
        total = (total & 15) + carry

    return format(total, '04b')


def calculate_checksum(data):
    blocks = []

    # Divide data into 4-bit blocks
    for i in range(0, len(data), 4):
        blocks.append(data[i:i + 4])

    # Add all blocks
    total = blocks[0]

    for block in blocks[1:]:
        total = ones_complement_add(total, block)

    # Take 1's complement
    checksum = ''.join(
        '1' if bit == '0' else '0'
        for bit in total
    )

    return checksum


# Input
data = input("Enter transmitted dataword: ")

# Make length a multiple of 4
while len(data) % 4 != 0:
    data = '0' + data

# Generate checksum
checksum = calculate_checksum(data)

# Create transmitted codeword
transmitted_codeword = data + checksum

print("\n========== TRANSMITTER ==========")
print("Dataword       :", data)
print("Checksum       :", checksum)
print("Codeword       :", transmitted_codeword)


# CASE 1: Error introduced
received_error = list(transmitted_codeword)

# Change the first bit
if received_error[0] == '0':
    received_error[0] = '1'
else:
    received_error[0] = '0'

received_error = ''.join(received_error)

final_checksum_error = calculate_checksum(received_error)

print("\n========== CASE 1: ERROR ==========")
print("Received codeword :", received_error)
print("Final checksum    :", final_checksum_error)

if final_checksum_error == "0000":
    print("Result            : ACCEPTED")
else:
    print("Result            : REJECTED")


# CASE 2: No error
received_no_error = transmitted_codeword

final_checksum_no_error = calculate_checksum(received_no_error)

print("\n========== CASE 2: NO ERROR ==========")
print("Received codeword :", received_no_error)
print("Final checksum    :", final_checksum_no_error)

if final_checksum_no_error == "0000":
    print("Result            : ACCEPTED")
else:
    print("Result            : REJECTED")