import os
import glob
import argparse


def main(args):

    for filename in glob.glob(os.path.join(args.source_directory, '**', '*.mdx'), recursive=True):
        basename = os.path.basename(filename).split(".")[0]

        print(f"Renaming {filename} to {basename.lower()}.mdx")

        new_path = os.path.join(os.path.dirname(filename), basename.lower() + ".mdx")
        os.rename(filename, new_path)
        print(f"Renamed {filename} to {new_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort MDX files into category directories based on their metadata.")
    parser.add_argument("--source-directory", required=True, help="The directory containing the MDX files to sort.")
    args = parser.parse_args()
    main(args)