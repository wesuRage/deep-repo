import git
import os
import pyfiglet
from concurrent.futures import ThreadPoolExecutor
from markdown_pdf import MarkdownPdf, Section
from openai import OpenAI
from pathlib import Path
from ollama import Client

font = "delta_corps_priest_1"

BOLD = "\033[1m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLUE = "\033[1;34m"
CYAN = "\033[1;36m"
RESET = "\033[0m"

os.system("clear")

print(f"{BLUE}", pyfiglet.figlet_format("DEEP", font))
print(f"{CYAN}", pyfiglet.figlet_format("REPO", font), f"{RESET}")

print(f"{BOLD}{BLUE}[*]{RESET} {BOLD}{UNDERLINE}A modular AI repository analyser and reporter.{RESET}\n")
print(f"Developed by: {BLUE}wesuRage {RESET}({BLUE}https://github.com/wesuRage{RESET})")
print(f"{ITALIC}Dedicated to my wife {CYAN}Dominique{RESET}.\n")

system_prompt = {"role": "system", "content": """
    You are made to analyse every piece of code of a file and
    it's functionalities. You are made to make reports in markdown
    of how the code works. You should give
    your opinion about the code on how to improve it, mentioning
    the file path and which line does the code begin. You must be
    extremely detailed about the code, showing snippets of it and
    talking about them and their functionalities"""}

black_list = [".git"]
files_list = []
full_content_to_analyse = []

def file_crawler(path: str):
    repo = Path(path)
    files = list(repo.rglob("*"))

    for file in files:
        if not any(part in black_list for part in file.parts) and file.is_file():
            if file.suffix.lower() not in black_list:
                files_list.append(get_file_tuple(str(file.absolute())))


def clone_repo(repo: str, branch: str):
    repo_path = f"/tmp/{repo.split('/')[-1]}"

    if os.path.exists(repo_path):
        return repo_path

    git.Repo.clone_from(repo, repo_path, branch=branch)

    return repo_path


def get_file_tuple(path: str):
    with open(path, "r") as file:
        content = file.read()

    file.close()

    return (path, content)


def analyse_repo_api(repo: str, file_name_path: str, file_content: str, client, model: str):
    print(f"{BOLD}{CYAN}[+] Analysing:{RESET} {file_name_path}...")

    messages = [
        system_prompt,
        {"role": "user", "content": f"FILE_NAME/PATH: {file_name_path}\n\nFILE_CONTENT:\n{file_content}"},
    ]


    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False
    )

    full_response = response.choices[0].message.content

    output_dir = f"analysis_results_{repo}"
    os.makedirs(output_dir, exist_ok=True)

    safe_file_name = file_name_path.replace("/tmp/", "").replace("/", "_").replace("\\", "_")
    output_path = os.path.join(output_dir, f"{safe_file_name}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_response)

def analyse_repo_local(repo: str, file_name_path: str, file_content: str, model: str):
    print(f"{BOLD}{CYAN}[+] Analysing:{RESET} {file_name_path}...")

    messages = [
        system_prompt,
        {"role": "user", "content": f"FILE_NAME/PATH: {file_name_path}\n\nFILE_CONTENT:\n{file_content}"},
    ]

    client = Client(
        host="http://localhost:11434",
        headers={"Content-Type": "application/json"}
    )

    response = client.chat(model=model, messages=messages)

    full_response = response["message"]["content"]

    output_dir = f"analysis_results_{repo}"
    os.makedirs(output_dir, exist_ok=True)

    safe_file_name = file_name_path.replace("/tmp/", "").replace("/", "_").replace("\\", "_")
    output_path = os.path.join(output_dir, f"{safe_file_name}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_response)


def analyse_reports(repo_name: str, client, model, local=False):
    repo = Path(f"analysis_results_{repo_name}")
    files = list(repo.rglob("*"))

    for file in files:
        if file.name != "PDF" and ".pdf" not in file.name and file.is_file():
            with open(file, "r") as f:
                full_content_to_analyse.append(f.read())
            f.close()

    project_analysis = ""

    system_prompt_report = {"role": "system", "content": """
        You are made to analyse every piece of code of a file and
        it's functionalities. You are made to make reports in markdown
        of how the code works. You should give
        your opinion about the code on how to improve it, mentioning
        the file path and which line does the code begin. You must be
        extremely detailed about the code, showing snippets of it and
        talking about them and their functionalities. Now, your goal is
        to join every single piece of information of what you receive,
        I mean EVERYTHING!!!! Don't you loose any tiny information of
        what get, it doesn't matter how huge it gets"""}

    if local:
        messages = [
            system_prompt_report,
            {"role": "user", "content": f"FILE_NAME/PATH: ALL_PROJECT_DATA\n\nFILE_CONTENT:\n{"".join(full_content_to_analyse)}"},
        ]

        client = Client(
            host="http://localhost:11434",
            headers={"Content-Type": "application/json"}
        )

        response = client.chat(model=model, messages=messages)

        project_analysis = response["message"]["content"]
    else:
        try:
            messages = [
                system_prompt_report,
                {"role": "user", "content": f"FILE_NAME/PATH: ALL_PROJECT_DATA\n\nFILE_CONTENT:\n{"".join(full_content_to_analyse)}"},
            ]

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False
            )

            project_analysis = response.choices[0].message.content
        except Exception as _:
            print(f"{BOLD}{BLUE}[-] ERROR: error while requesting to the full project analysis. Maybe the project is too big to analyse at once.{RESET}")
            locally = input(f"{BOLD}[?] Maybe would you want to run the full project analysis on your device? (y/N) {BLUE}>>>{RESET} ")

            if not locally.lower() in ["y", "yes"]:
                print(f"{ITALIC}Aborting...{RESET}")
                exit(0)

            content = "".join(full_content_to_analyse)

            print(content)

            messages = [
                system_prompt_report,
                {"role": "user", "content": f"FILE_NAME/PATH: ALL_PROJECT_DATA\n\nFILE_CONTENT:\n{content}"},
            ]

            client = Client(
                host="http://localhost:11434",
                headers={"Content-Type": "application/json"}
            )

            model = input(f"[*] OLLAMA MODEL (default 'qwen2.5:0.5b') {BLUE}>>>{RESET} ")

            response = client.chat(model=model if model else "qwen2.5:0.5b", messages=messages)

            project_analysis = response["message"]["content"]

    with open(f"analysis_results_{repo_name}/{repo_name}_report.md", "w") as f:
        f.write(project_analysis)
    f.close()


def main():
    repo = input(f"[*] REPO {BLUE}>>>{RESET} ")
    repo_name = repo.split("/")[-1]

    branch = input(f"[*] BRANCH (default 'main') {BLUE}>>>{RESET} ")
    add_to_black_list = input(f"[*] Would you like a custom black-list? (y/N) {BLUE}>>>{RESET} ")

    if add_to_black_list.lower() in ["y", "yes"]:
        while True:
            black_list_item = input(f"[-] (blank for done) {BLUE}>>>{RESET} ")

            if not black_list_item:
                break

            black_list.append(black_list_item)

    model = ""
    api_key = ""

    local_or_api = input(f"[*] Run locally(1) or using an API(2)? {BLUE}>>>{RESET} ")

    if local_or_api == "1":
        model = input(f"[*] OLLAMA MODEL (default 'qwen2.5:0.5b') {BLUE}>>>{RESET} ")
    elif local_or_api == "2":
        model = input(f"[*] Choose: deepseek-chat/gpt-4o/gpt-4o-mini? {BLUE}>>>{RESET} ")
        api_key = input(f"[*] API KEY {BLUE}>>>{RESET} ")

    multi_threading = input(f"[*] Enable multi-threading? (y/N) {BLUE}>>>{RESET} ")

    repo_path = clone_repo(repo, branch if branch else "main")
    file_crawler(repo_path)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com" if model == "deepseek-chat" else "https://api.openai.com/v1")

    if multi_threading.lower() in ["y", "yes"]:

        max_workers = int(input(f"[*] Number of Workers {BLUE}>>>{RESET} "))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for file in files_list:
                if local_or_api == "1":
                    executor.submit(analyse_repo_local, repo_name, file[0], file[1], model if model else "qwen2.5:0.5b")
                elif local_or_api == "2":
                    executor.submit(analyse_repo_api, repo_name, file[0], file[1], client, model)


    else:
        for file in files_list:
            if local_or_api == "1":
                analyse_repo_local(repo_name, file[0], file[1], model if model else "qwen2.5:0.5b")
            elif local_or_api == "2":
                analyse_repo_api(repo_name, file[0], file[1], client, model)

    print(f"{BOLD}{BLUE}[*] Individual analysis completed!{RESET}")
    print(f"{BOLD}{CYAN}[+] Starting reports analysis...{RESET}")

    analyse_reports(repo_name, client, model)

    print(f"{BOLD}{BLUE}[+] Reports analysis completed!{RESET}")
    print(f"{BOLD}{CYAN}[+] Generating PDF...{RESET}")

    os.makedirs(os.path.join(os.getcwd() + f"/analysis_results_{repo_name}", "PDF"), exist_ok=True)

    pdf = MarkdownPdf(toc_level=2)

    user_css = "h1, h2, h3, h4, h5, h6, bold { color: #3E76FD; }"

    with open(f"analysis_results_{repo_name}/" + repo_name + "_report.md", "r") as f:
        content = f.read()
        pdf.add_section(Section(content, toc=False), user_css=user_css)
        pdf.save(f"analysis_results_{repo_name}/PDF/{repo_name}_report.pdf")

    print(f"{BOLD}{BLUE}[+] PDF reports can be found at: analysys_results_{repo_name}/PDF {RESET}")


if __name__ == "__main__":
    main()
