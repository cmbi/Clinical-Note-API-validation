import json
import sys

from pipeline import validate_clinical_notes


def main():
    if len(sys.argv) != 4:
        print("Usage: python main.py input.json output.json errors.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    error_file = sys.argv[3]

    # Read input file
    with open(input_file, "r", encoding="utf-8") as file:
        json_data = json.load(file)

    # Retrieve results
    validated_data, errors = validate_clinical_notes(json_data)

    # Write results
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(validated_data, file, indent=4, ensure_ascii=False)
        file.write("\n")

    # Write errors
    with open(error_file, "w", encoding="utf-8") as file:
        json.dump(errors, file, indent=4, ensure_ascii=False)
        file.write("\n")


if __name__ == "__main__":
    main()
