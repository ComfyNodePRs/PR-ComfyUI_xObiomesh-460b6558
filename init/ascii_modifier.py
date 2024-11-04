def modify_ascii_art(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified_lines = []
    for line in lines:
        if len(line.strip()) > 18:  # Only process lines long enough to have first/last 9 chars
            # Keep first 9 and last 9 characters, replace middle with spaces
            first_nine = line[:9]
            last_nine = line[-10:]  # -10 to include newline if present
            middle_length = len(line) - 18
            middle_spaces = ' ' * middle_length
            modified_line = first_nine + middle_spaces + last_nine
        else:
            modified_line = line  # Keep short lines unchanged
        modified_lines.append(modified_line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

# Example usage
input_file = 'init/ascii/xO_bigblue.txt'
output_file = 'init/ascii/xO_bigblue_modified.txt'
modify_ascii_art(input_file, output_file) 