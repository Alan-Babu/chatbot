#Run Pthon service
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

#Run ollama phi3 service
install ollama locally https://ollama.com/download/windows
ollama pull phi3
ollama run phi3  

#Run Node
npm start
