<div align="center">

<h1> ⭐  AMD AI Vision Agent ⭐ </h1>
meow
<div align="left">

<!-- TABLE OF CONTENTS -->

<details>
  <summary>✨ Table of Contents ✨ </summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#how-it-works">How it Works</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a>
      <ul>
        <li><a href="#examples">Examples</a></li>
      </ul></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## 🌟 About The Project 🌟

Model Context Protocols (MCPs) have brought a new perspective on AI and Large Language Models (LLMs), emerging as a powerful tool able to connect multiple models and APIs to remote machines. The  open-source framework works similar to REST API and provides an interface that allows models to interact with data and context, universalizing the way that AI agents integrate into systems. This project demonstrates the capabilities of MCPs and how they can be used with AMD ROCm machines. The repository contains a Docker Compose file that uses vLLM to build an AI vision agent that has function calling capabilities. It contains tools and functionalities to segment images of documents as well as add color filters. 

This AI Vision Agent will allow users to quickly and easily be able to process images with an MCP server that provides segmentation tools, color filters for accessibility, and basic image functions such as crop and resize. 

### ✨ How it Works ✨

* ![architecture](assets/arch.png)

The AI agent uses Open WebUI for its user interface, which allow for a seamless integration with Whisper and Kokoro for STT and TTS capabilities. For the OpenAI model connecton, it uses the rocm instance of vllm to serve the Salesforce xLAM 2 model. The xLAM series is known for its effectiveness with native tool calling and xLAM hosts its own tool parser which is used for auto tool choice. Open WebUI uses MCPO for its MCP client connection, which hosts the MCP as a tool server; however, this limits the MCP to just its tool capabilities.

MCPO exposes the tools on the MCP server to the AI agent on Open WebUI allowing the agent to choose whichever tools it may need for a request. The Poetry MCP tools can separated into two categories. One, labeled using "get", fetches data from a Poetry Foundation dataset loaded into the server using SQLite queries. The other, labeled using "become", uses OpenAPI chat completions for guided word generation or feedback generation. The chat completions use the same model as the one backing the Open WebUI AI agent; however, it works separately from the agent. There are two vllm endpoints that run simultaneously. Both use the same model for reasoning; however, they are fed different context and system prompts, and therefore, are assigned different tasks to complete. This is necessary, because the xLAM model on its own is prone to hallucination when tasked with generation of constructive criticism or rhymes, and must be guided with the necessary system prompts to provide the most accurate information as possible.

The response from each tool that the AI agent calls is then fed back into the agent where it decides if the information that it has is enough to answer the user input. If it is not, it cycles through the tool calling cycle until it decides that the information is enough. Once the AI Agent reaches that point, it builds a response using the information that it retrieved from the tool calls and returns that back out to the user.

* ![flowchart](assets/flowchart.drawio.png)

<!-- GETTING STARTED -->

## 🌟 Getting Started 🌟

### ✨ Prerequisites ✨

* **Linux**: see the [supported Linux distributions](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html#supported-operating-systems).
* **ROCm**: see the [installation instructions](https://rocm.docs.amd.com/projects/ install-on-linux/en/latest/tutorial/quick-start.html).
* **GPU**: AMD Instinct™ MI300X accelerator or [other ROCm-supported GPUs](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html).
* **Docker**: with Docker Compose - [install](https://docs.docker.com/engine/install/).

### ✨ Installation ✨

1. Clone the repo
   
   ```sh
   git clone https://github.com/github_username/repo_name.git
   ```
2. Change git remote url to avoid accidental pushes to base project
   
   ```sh
   git remote set-url origin github_username/repo_name
   git remote -v # confirm the changes
   ```
3. Run the docker compose file to build and start up the containers
   
   ```sh
   docker compose up -d
   ```

* The current docker compose file is set up with the model Llama-xLAM-2-70b-fc-r, which is optimized for function calling capabilities. To change the model, replace the command parameter of the vllm service with:
  
  ```yaml
  command: ["/bin/sh", 
            "-c", 
            "vllm serve <model_name> 
            --port 8001 --enforce-eager 
            --gpu-memory-utilization 0.95 --tensor-parallel-size 2"]
  ```
* Make sure to set up the vllm container to direct to your local models folder. You can do this by modifying the volumes parameter
  
  ```yaml
  volumes:
    - </path/to/your/models>:/hf_home
  ```
* Ensure that the OpenWebUI container is redirected to the proper local path
  
  ```yaml
  volumes:
    - volumes:
      - </path/to/your/repository>/open-webui:/app/backend/data
  ```
* The AI agent should automatically connect to the OpenWebUI image. If it does not, simply go to the `admin panel`, and in `settings` under `connections` add a new connection with the url `http://vllm:8000/v1` and verify the connection.

4. To stop the Ai Agent, simply do
   
   ```sh
   docker compose down
   ```

## 🌟 Usage 🌟

✨ **If you are using the Poetry MCP Server**
The Poetry mcp server code is set up in the `/mcp` directory which contains the scripts to run the MCP server as well as a separate README for the server contianing information about the recommended setup for Open WebUI.

To set up the model, go to Open WebUI's workspace tab located on the left panel and in `Models`, create a new model titled "Poetry AI Assistant". In the custom model's settings, set the system prompt to the value stored under `System Prompt` in `mcp/setup.txt`. Choose the Base Model and save changes.
Next, go to the `admin panel`, and find the model that is connected to your OpenAI base url. Change that model's system prompt to the value stored under `Model Prompt` in setup.txt. Save the changes.
This will allow you to use a singular model as two separate AI agents, ensuring that all tool functions are called correctly.

✨ **If you are hosting the base MCP server**

* The base MCP server uses the same underlying architecture of the Poetry MCP server to query and insert into any labeled dataset.
* First upload your database into the base-mcp folder as `database.xlsx` file or replace the existing file with your dataset and modify the code if need be.
* A separate Dockerfile is provided for the base MCP as `Dockerfile.base` in the parent directory. Ensure that the all of the necessary files in base-mcp are copied in the Dockerfile.
* Modify the Docker Compose so that the `dockerfile` parameter is set to `Dockerfile.base`
* Modify the `NUM_COLS` environment variable in the docker compose to be the number of data columns in your dataset
* You can startup the server normally, but ensure that Open WebUI is configured for your application. 

The MCP server should automatically connect to the running OpenWebUI image. If it does not, simply go to `settings` and add a new tool server with the server url.

### ✨ Examples ✨

This is the Open WebUI with the Poetry AI agent

* ![tools](assets/home.png)

This is what the MCP server shows up as on Open WebUI.

* ![mcp1](assets/mcp.png)

Prompting the MCP server for a random poem by W.B. Yeats. Shows tool-chaining and native function calling. The AI agent first searches for a poem by Yeats under the name "random". Then retrieves a list of all poems written by Yeats and randomly selects a poem title. It then searches for that poem in the database and returns the full poem.

* ![logs](assets/random2.png)

Asking the MCP server for Yeats main themes. Shows post-processing of tool calls, as the MCP tool returns all poems and corresponding tags by Yeats and agent has to process that information to find top most common tags.

* ![logs](assets/theme.png)

Asking the AI agent for a rhyme.

* ![logs](assets/rhyme1.png)

Rhyme response:

* ![logs](assets/rhyme2.png)

Asking the AI agent for synonyms and response using the same poem from the previous chat.

* ![logs](assets/thesaurus.png)

## 🌟 Troubleshooting 🌟

* If Kokoro does not connect using the `localhost` url:
  Find the docker container network url. In VSCode, locate the docker tab on the left menu bar and locate the parent docker container under the `networks` section and open the corresponding file. Find the network url for the Kokoro container in the file.
  
  In Open WebUI, open the admin panel, and click the `Audio` tab. Under TTS, change the engine to `OpenAI`. Fill in the OpenAI base url with the docker container network url and fill in the OpenAI key with `not-needed`. Change the model name to `Kokoro`. To see all voices available, go to `http://localhost:8880/docs`.
* If STT does not work:
  Try adding audio types to the "Supported MIME Types" field in the `Audio` admin panel setting.

<!-- CONTACT -->

## 🌟 Contact 🌟

Amy Suo - amysuwoah@gmail.com / amy.suo@amd.com / as331@rice.edu

Project Link: [https://github.com/luminarchy/AMD-2025-AI-Agent-Demo](https://github.com/luminarchy/AMD-2025-AI-Agent-Demo)

<!-- ACKNOWLEDGMENTS -->

## 🌟 Acknowledgments 🌟

* [AMD ROCm Blogs](https://rocm.blogs.amd.com/)
* [the random person on reddit who made the poetry foundation dataset](https://www.kaggle.com/datasets/tgdivy/poetry-foundation-poems)

