import React, { useState } from "react"
import { TextField, Button, Typography, Box } from "@mui/material"

function App() {
  const [apiKey, setApiKey] = useState("")
  const [file, setFile] = useState(null)
  const [result, setResult] = useState("")

  const handleApiKeyChange = (event) => {
    setApiKey(event.target.value)
  }

  const handleFileChange = (event) => {
    setFile(event.target.files[0])
  }

  const handleFileUpload = () => {
    if (!file) {
      return
    }

    const isVideo = file.type.startsWith("video/")

    if (isVideo) {
      const ffmpeg = require("ffmpeg-static")
      const { createFFmpeg } = require("@ffmpeg/ffmpeg")
      const ffmpegInstance = createFFmpeg({ log: true })

      const convertToMp3 = async () => {
        try {
          await ffmpegInstance.load(ffmpeg)
          ffmpegInstance.FS("writeFile", "input.mp4", await fetchFile(file))
          await ffmpegInstance.run(
            "-i",
            "input.mp4",
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ac",
            "2",
            "-qscale:a",
            "4",
            "-ar",
            "48000",
            "output.mp3"
          )
          const data = ffmpegInstance.FS("readFile", "output.mp3")
          const mp3File = new File([data.buffer], "output.mp3", {
            type: "audio/mpeg",
          })
          setFile(mp3File)
        } catch (error) {
          console.log(error)
        }
      }

      const fetchFile = async (file) => {
        const response = await fetch(URL.createObjectURL(file))
        const arrayBuffer = await response.arrayBuffer()
        return new Uint8Array(arrayBuffer)
      }

      convertToMp3()
    }

    // Code to upload file to server
  }

  const handleCalculate = () => {
    // Code to calculate result using API key and uploaded file
    setResult("Result: 42")
  }

  const handleFileDrop = (event) => {
    event.preventDefault()
    setFile(event.dataTransfer.files[0])
  }

  return (
    <Box
      sx={{ m: 2 }}
      onDrop={handleFileDrop}
      onDragOver={(event) => event.preventDefault()}
    >
      <Typography variant="h4" gutterBottom>
        API Key
      </Typography>
      <TextField
        label="Enter API key"
        variant="outlined"
        value={apiKey}
        onChange={handleApiKeyChange}
        fullWidth
        sx={{ mb: 2 }}
      />
      <Typography variant="h4" gutterBottom>
        Upload File
      </Typography>
      <Box
        sx={{
          border: file ? "2px dashed grey" : "1px dashed grey",
          borderRadius: "5px",
          padding: "10px",
          textAlign: "center",
          mb: 2,
        }}
      >
        <Typography variant="body1" sx={{ mb: 1 }}>
          Drag and drop file here, or click to select file
        </Typography>
        <input type="file" onChange={handleFileChange} sx={{ mb: 2 }} />
      </Box>
      <Button variant="contained" onClick={handleFileUpload}>
        Upload
      </Button>
      <Typography variant="h4" gutterBottom>
        Calculate Result
      </Typography>
      <Button variant="contained" onClick={handleCalculate}>
        Calculate
      </Button>
      <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
        {result}
      </Typography>
    </Box>
  )
}

export default App
