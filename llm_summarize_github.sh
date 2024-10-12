python llm_summarize.py \
  --max-chunk-tokens 8000 \
  --overlap-tokens 500 \
  --second-level-max-chunk-tokens 100000 \
  --output-file final_summary_all.md \
  --dump-combined-summary combined_summary_all.txt \
  --prompt-instructions "List the issues/PRs in the following content. For each issue or PR, just list title linked with URL, state, submitter, tags and concisely-summarized description. Please don't miss any issue or PR." \
  --second-level-prompt "Split the content into either Issue or PR section. Then in each section, further categorize issues and PRs according to their titles and descriptions. Please note that issues or PRs might duplicate since the content are concatenated from chunks. Please combine same issues/PRs into one. Do not keep tags. Use markdown format."
