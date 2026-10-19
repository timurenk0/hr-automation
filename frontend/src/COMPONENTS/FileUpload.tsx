import { Button } from "@mui/material";
import { useState } from "react"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import { useMutation } from "@tanstack/react-query";

const FileUpload = () => {
    const [file, setFile] = useState<File | null>(null);
    const [fileContent, setFileContent] = useState({
        links: {},
        content: ""
    });

    const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;

        if (!files || files.length < 1) {
            setFile(null);
            return;
        }

        setFile(files[0]);
    }

    const uploadMutation = useMutation({
        mutationFn: async () => {
            if (!file) {
                console.error("No file");
                return;
            }
            
            const formData = new FormData();
            formData.append("pdf", file);
            
            const res = await fetch("http://localhost:8000/api/upload-pdf", {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            if (!res.ok) {
                console.error(data);
                return;
            }


            console.log(data);
            setFileContent(data)
            return data;
        }
    });

  
  return (
    <div>
        <div className="flex">
            <Button content="label" variant="outlined">
                <input type="file" accept=".pdf" onChange={handleInput} />
            </Button>
            <Button size="small" variant="contained" endIcon={<UploadFileIcon />} onClick={() => uploadMutation.mutate()}>Upload</Button>
        </div>
        <p>File Size: {file ? `${(file.size/1000/1000).toFixed(2)} MB` : 0}</p>

        <ul>
            {Object.entries(fileContent.links).map(([k, v]) => (
                <li key={k}><b>{k}</b>: {v ? <a target="_blank" className="underline text-sky-500" href={String(v)}>{String(v)}</a> : "Not found"}</li>
            ))}
        </ul>

        {fileContent.content}
    </div>
  )
}

export default FileUpload