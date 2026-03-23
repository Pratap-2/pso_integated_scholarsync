from cv_parser import CVParser
import traceback

def main():
    try:
        p = CVParser()
        print("Parsing...")
        res = p.parse_cv("test_resume.txt") # dummy text file
        print("RESULT:")
        print(res)
    except Exception as e:
        print("ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
