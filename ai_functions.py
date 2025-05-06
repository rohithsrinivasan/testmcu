from typing import Union, Dict
import pandas as pd
import google.generativeai as genai

def Add_Description_for_pin(
    df: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    gemini_api_key: str,
    model_name: str = "gemini-1.5-flash"  # Updated default model
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Adds application-focused descriptions to pins using Gemini API.
    
    Args:
        df: Input DataFrame or dictionary of DataFrames
        gemini_api_key: Gemini API key for authentication
        model_name: Name of the Gemini model to use (default: gemini-1.5-flash)
        
    Returns:
        DataFrame or dictionary of DataFrames with 'Description' column filled
    """
    # Configure Gemini API with the provided key
    try:
        genai.configure(api_key=gemini_api_key)
        # Initialize with the specified model
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Failed to initialize Gemini API: {e}")
        return df
    
    # def generate_pin_description(row: pd.Series) -> str:
    #     """
    #     Generates an application-focused description for a pin using Gemini API.
    #     """
    #     # Build the pin identifier string
    #     try:
    #         pin_identifier = str(int(float(row['Pin Designator'])))  # Handles float/int/string
    #     except:
    #         pin_identifier = str(row['Pin Designator'])
            
    #     if pd.notna(row.get('Pin Alternate Name')):
    #         pin_identifier += f" ({row['Pin Alternate Name']})"
        
    #     prompt = f"""Generate a 12-15 word application-focused description for an IC pin. Focus on:
    #     - What the pin is typically used for in real circuits
    #     - Common components it connects to
    #     - Its role in the system

    #     Pin: {pin_identifier}
    #     Type: {row['Electrical Type']}
    #     Group: {row.get('Changed Grouping', '')}
    #     Side: {row.get('Side', '')}

    #     Examples:
    #     "Connects to crystal resonator for main clock generation"
    #     "Outputs system clock to synchronize peripheral devices"

    #     Respond ONLY with the description, no prefixes or quotes."""
        
    #     try:
    #         # Using the newer generate_content method
    #         response = model.generate_content(prompt)
    #         if not response.text:
    #             raise ValueError("Empty response from API")
    #         description = response.text.strip().strip('"').strip("'")
    #         # Enforce word limit and clean up
    #         words = description.split()[:15]
    #         return ' '.join(words)
    #     except Exception as e:
    #         print(f"Error generating description for pin {pin_identifier}: {e}")
    #         # Fallback description using available data
    #         return f"{pin_identifier} {row['Electrical Type']} for {row.get('Changed Grouping', 'circuit')}"
    

    def generate_pin_description(row: pd.Series) -> str:
        """
        Generates a connection-focused description for a pin using Gemini API.
        """
        # Build the pin identifier string
        try:
            pin_identifier = str(int(float(row['Pin Designator'])))  # Handles float/int/string
        except:
            pin_identifier = str(row['Pin Designator'])
            
        if pd.notna(row.get('Pin Alternate Name')):
            pin_identifier += f" ({row['Pin Alternate Name']})"
            
        
        prompt = f"""Generate a 12-15 word description specifically about where this IC pin connects in typical applications.
        Focus ONLY on:
        - Specific components it would connect to (e.g., "to voltage regulator output")
        - Typical connection paths not obvious from pin name/type
        - Physical connection details
        
        DO NOT mention:
        - The obvious electrical type (we already know it's {row['Electrical Type']})
        - The grouping (we already know it's {row.get('Changed Grouping', '')})
        
        Pin: {pin_identifier}
        Existing Info: {row['Electrical Type']} {row.get('Pin Alternate Name', '')}
        
        Examples:
        "Connects to output of 3.3V LDO regulator with 10μF decoupling capacitor"
        "Routes to crystal oscillator with 22pF load capacitors"
        "Bonds to PCB ground plane through multiple vias"
        
        Respond ONLY with the connection details:"""
        
        try:
            response = model.generate_content(prompt)
            if not response.text:
                raise ValueError("Empty response from API")
            description = response.text.strip().strip('"').strip("'")
            # Enforce word limit and clean up
            words = description.split()[:18]  # Slightly longer for technical details
            return ' '.join(words)
        except Exception as e:
            print(f"Error generating description for pin {pin_identifier}: {e}")
            # Fallback connection-focused description
            return f"-"

    def process_single_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes a single DataFrame to add descriptions.
        Skips rows with Electrical Type == "I/O"
        """
        df_copy = df.copy()
        required_cols = [
            'Pin Designator', 
            'Electrical Type',
            'Changed Grouping',
            'Description'
        ]
        
        # Validate columns
        missing_cols = [col for col in required_cols if col not in df_copy.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Detect empty descriptions excluding I/O pins
        empty_mask = (
            (df_copy['Description'].isna() | df_copy['Description'].astype(str).str.strip().eq('')) &
            ~df_copy['Electrical Type'].str.upper().eq('I/O')  # Skip I/O types
        )
        
        if empty_mask.any():
            df_copy.loc[empty_mask, 'Description'] = df_copy[empty_mask].apply(
                generate_pin_description, 
                axis=1
            )
        
        # For rows with Electrical Type == I/O and blank description, explicitly set as blank
        io_mask = (
            (df_copy['Description'].isna() | df_copy['Description'].astype(str).str.strip().eq('')) &
            df_copy['Electrical Type'].str.upper().eq('I/O')
        )
        df_copy.loc[io_mask, 'Description'] = ''

        return df_copy



    def process_single_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes a single DataFrame to add descriptions.
        """
        df_copy = df.copy()
        required_cols = [
            'Pin Designator', 
            'Electrical Type',
            'Changed Grouping',
            'Description'
        ]
        
        # Validate columns
        missing_cols = [col for col in required_cols if col not in df_copy.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Detect empty descriptions (handles NaN, None, and empty strings)
        empty_mask = (
            df_copy['Description'].isna() | 
            (df_copy['Description'].astype(str).str.strip() == '')
        )
        
        # Process only rows with empty descriptions
        if empty_mask.any():
            df_copy.loc[empty_mask, 'Description'] = df_copy[empty_mask].apply(
                generate_pin_description, 
                axis=1
            )
        
        return df_copy
    
    try:
        # Handle dictionary case
        if isinstance(df, dict):
            return {name: process_single_df(table) for name, table in df.items()}
        
        # Handle single DataFrame case
        return process_single_df(df)
    except Exception as e:
        print(f"Error in Add_Description_for_pin: {e}")
        return df
    

####################################################################################

