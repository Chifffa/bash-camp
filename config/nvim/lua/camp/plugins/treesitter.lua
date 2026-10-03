-- nvim-treesitter: highlighting and text objects from syntax trees.
return {
  "nvim-treesitter/nvim-treesitter",
  branch = "main",
  lazy = false,
  build = ":TSUpdate",
  config = function()
    -- The parsers are compiled from source. Without a compiler every start would retry and fail;
    -- Neovim's built-in parsers, for C, Lua, Markdown and Vim, have to do then.
    if vim.fn.executable("tree-sitter") == 1 and vim.fn.executable("cc") == 1 then
      require("nvim-treesitter").install({
        "bash",
        "c",
        "cmake",
        "cpp",
        "cuda",
        "dockerfile",
        "gitignore",
        "go",
        "gomod",
        "html",
        "json",
        "latex",
        "lua",
        "make",
        "markdown",
        "markdown_inline",
        "proto",
        "python",
        "rust",
        "toml",
        "vim",
        "vimdoc",
        "yaml",
      })
    end

    vim.api.nvim_create_autocmd("FileType", {
      pattern = "*",
      callback = function()
        if vim.treesitter.language.get_lang(vim.bo.filetype) then
          pcall(vim.treesitter.start)
        end
      end,
    })
  end,
}
