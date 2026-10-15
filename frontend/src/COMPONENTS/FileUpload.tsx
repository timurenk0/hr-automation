import { Button } from "@mui/material";
import { useState } from "react"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import { useMutation } from "@tanstack/react-query";

const FileUpload = () => {
    const [file, setFile] = useState<File | null>(null);

    const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;

        if (!files || files.length < 1) {
            setFile(null);
            return;
        }

        setFile(files[0]);
    }

    // const uploadMutation = useMutation({
    //     mutationFn: async () => {
    //     }
    // });

    const uploadMutation = () => {
        if (!file) {
            alert("Select a file first!");
            return;
        }
        
        alert("File uploaded! (mock implementation)");
        return;
    }
  
  return (
    <div>
        <div className="flex">
            <Button content="label" variant="outlined">
                <input type="file" accept=".pdf" onChange={handleInput} />
            </Button>
            <Button size="small" variant="contained" endIcon={<UploadFileIcon />} onClick={uploadMutation}>Upload</Button>
        </div>
        <p>File Size: {file ? `${(file.size/1000/1000).toFixed(2)} MB` : 0}</p>
    </div>
  )
}

export default FileUpload