import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict


class FileDeduplicator:
    def __init__(self, folder_path: str):
        """Initialize with the folder path containing Excel and CSV files."""
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

    def find_files(self) -> List[Path]:
        """Find all Excel and CSV files in the folder."""
        return sorted(
            [f for f in self.folder_path.glob("**/*") if f.suffix in ('.xls', '.xlsx', '.csv')],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

    def get_newest_file(self) -> Tuple[Path, List[Path]]:
        """Get the newest file and list of older files."""
        files = self.find_files()
        if not files:
            raise FileNotFoundError("No Excel or CSV files found in the specified folder")
        return files[0], files[1:]

    def load_and_combine_files(self, files: List[Path]) -> pd.DataFrame:
        """Load and combine multiple Excel and CSV files into a single DataFrame."""
        combined_data = pd.DataFrame()
        for file in files:
            try:
                if file.suffix in ('.xls', '.xlsx'):
                    xls = pd.ExcelFile(file)
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(file, sheet_name=sheet_name)
                        if not df.empty:
                            combined_data = pd.concat([combined_data, df], ignore_index=True)
                elif file.suffix == '.csv':
                    df = pd.read_csv(file, low_memory=False)
                    if not df.empty:
                        combined_data = pd.concat([combined_data, df], ignore_index=True)
            except Exception as e:
                print(f"Error reading file {file}: {str(e)}")
        return combined_data.drop_duplicates() if not combined_data.empty else combined_data

    def process_newest_file(self, newest_file: Path, combined_data: pd.DataFrame, columns_to_compare: List[str]) -> Dict[str, Dict[str, int]]:
        """Process the newest file and remove duplicates. Returns statistics about removals."""
        backup_path = newest_file.with_name(f"{newest_file.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{newest_file.suffix}")
        removal_stats = {}

        try:
            # Create backup
            os.replace(newest_file, backup_path)

            # Process file
            if newest_file.suffix in ('.xls', '.xlsx'):
                xls = pd.ExcelFile(backup_path)
                with pd.ExcelWriter(newest_file, engine='openpyxl') as writer:
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(backup_path, sheet_name=sheet_name)
                        if not df.empty:
                            self._process_dataframe(df, combined_data, columns_to_compare, removal_stats, sheet_name, writer)
            elif newest_file.suffix == '.csv':
                df = pd.read_csv(backup_path, low_memory=False)
                if not df.empty:
                    self._process_dataframe(df, combined_data, columns_to_compare, removal_stats)
                    # Save the processed CSV file using the stored DataFrame
                    self.df_final.to_csv(newest_file, index=False)  # This is the fix

            print(f"\nSuccessfully processed file: {newest_file}")
            print(f"Backup created at: {backup_path}")

            self._print_statistics(removal_stats)
            return removal_stats

        except Exception as e:
            # Restore original file if something goes wrong
            if backup_path.exists() and not newest_file.exists():
                os.replace(backup_path, newest_file)
            raise Exception(f"Error processing file: {str(e)}")

    def _process_dataframe(self, df: pd.DataFrame, combined_data: pd.DataFrame, columns_to_compare: List[str],
                           removal_stats: Dict, sheet_name: str = 'CSV', writer=None):
        """Helper to process individual DataFrame and update statistics."""
        original_count = len(df)
        
        # If the column is specified as 'B', use the second column (index 1)
        if columns_to_compare == ['B']:
            # Get the actual column name from the second column
            columns_to_compare = [df.columns[1]]

        # Validate column names
        for col in columns_to_compare:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in the file.")

        # Remove internal duplicates
        df_no_internal_dupes = df.drop_duplicates(subset=columns_to_compare)
        internal_dupes_removed = original_count - len(df_no_internal_dupes)

        # Remove external duplicates
        if not combined_data.empty:
            df_final = df_no_internal_dupes[~df_no_internal_dupes.set_index(columns_to_compare).index.isin(
                combined_data.set_index(columns_to_compare).index)]
            external_dupes_removed = len(df_no_internal_dupes) - len(df_final)
        else:
            df_final = df_no_internal_dupes
            external_dupes_removed = 0

        # Save results
        if writer and sheet_name != 'CSV':
            df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        else:  # This is the fix for CSV files
            self.df_final = df_final  # Store the final DataFrame for CSV processing
            
        # Update stats
        removal_stats[sheet_name] = {
            'original_rows': original_count,
            'internal_duplicates_removed': internal_dupes_removed,
            'external_duplicates_removed': external_dupes_removed,
            'remaining_rows': len(df_final)
        }

    def _print_statistics(self, removal_stats: Dict):
        """Print detailed statistics."""
        print("\nDuplication Removal Statistics:")
        print("=" * 50)
        for sheet_name, stats in removal_stats.items():
            print(f"\nSheet: {sheet_name}")
            print(f"  Original rows: {stats['original_rows']}")
            print(f"  Internal duplicates removed: {stats['internal_duplicates_removed']}")
            print(f"  External duplicates removed: {stats['external_duplicates_removed']}")
            print(f"  Total duplicates removed: {stats['internal_duplicates_removed'] + stats['external_duplicates_removed']}")
            print(f"  Remaining unique rows: {stats['remaining_rows']}")
            print(f"  Reduction percentage: {((stats['original_rows'] - stats['remaining_rows']) / stats['original_rows'] * 100):.1f}%")

    def remove_duplicates(self) -> None:
        """Main method to handle the deduplication process."""
        try:
            # Get files
            newest_file, older_files = self.get_newest_file()

            print(f"\nNewest file detected: {newest_file}")
            print("\nAll Excel and CSV files found (newest first):")
            for i, file in enumerate(self.find_files(), 1):
                print(f"{i}: {file}")

            choice = input("\nIs this the correct newest file? (yes/no/quit): ").strip().lower()
            if choice in ['quit', 'q']:
                return
            if choice in ['no', 'n']:
                idx = int(input("\nEnter the number of the correct file: ")) - 1
                files = self.find_files()
                newest_file = files[idx]
                older_files = [f for f in files if f != newest_file]

            # Load and process files
            print("\nLoading older files...")
            combined_data = self.load_and_combine_files(older_files)
            print(f"Found {len(combined_data)} unique rows in older files")

            # Use column 'B' by default
            columns_to_compare = ['B']

            print("\nProcessing newest file...")
            self.process_newest_file(newest_file, combined_data, columns_to_compare)

        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Operation aborted")


if __name__ == "__main__":
    folder_path = "data_csv"
    deduplicator = FileDeduplicator(folder_path)
    deduplicator.remove_duplicates()
