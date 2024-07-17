import streamlit as st
import wx
import os

def open_directory_dialog():
    app = wx.App(False)
    dialog = wx.DirDialog(None, "Choose a directory", style=wx.DD_DEFAULT_STYLE)
    if dialog.ShowModal() == wx.ID_OK:
        path = dialog.GetPath()
    else:
        path = None
    dialog.Destroy()
    return path

def main():
    st.title("Streamlit App")

    if st.button("Select Directory"):
        directory = open_directory_dialog()
        if directory:
            st.write(f"Selected directory: {directory}")
            # Add your file download logic here
            file_content = "This is a dummy file."
            file_path = os.path.join(directory, "dummy_file.txt")

            with open(file_path, 'w') as file:
                file.write(file_content)

            st.write(f"File has been created at: {file_path}")
        else:
            st.write("No directory selected.")

if __name__ == "__main__":
    main()