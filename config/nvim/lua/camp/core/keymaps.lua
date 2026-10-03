-- Keymaps that need no plugin; each plugin's own are in its spec.

vim.g.mapleader = " "

local map = vim.keymap.set

-- Sessions, one per working directory.
local session_dir = vim.fn.stdpath("state") .. "/sessions"

local function session_file()
  local name = vim.fn.getcwd():gsub("[/\\:]", "%%")
  return session_dir .. "/" .. name .. ".vim"
end

local function save_session()
  vim.fn.mkdir(session_dir, "p")
  vim.cmd("mksession! " .. vim.fn.fnameescape(session_file()))
  vim.notify("Session saved", vim.log.levels.INFO)
end

local function restore_session()
  local file = session_file()
  if vim.fn.filereadable(file) == 0 then
    vim.notify("No session for current directory", vim.log.levels.WARN)
    return
  end

  vim.cmd("silent! %bwipeout!")
  vim.cmd("source " .. vim.fn.fnameescape(file))
  vim.notify("Session restored", vim.log.levels.INFO)
end

vim.api.nvim_create_user_command("SessionSave", save_session, {})
vim.api.nvim_create_user_command("SessionRestore", restore_session, {})
map("n", "<leader>qs", save_session, { desc = "Save Session" })
map("n", "<leader>qr", restore_session, { desc = "Restore Session" })

-- Windows and tabs.
map("n", "<leader>w|", "<C-w>v", { desc = "Split Window Vertically" })
map("n", "<leader>w-", "<C-w>s", { desc = "Split Window Horizontally" })
map("n", "<leader>w=", "<C-w>=", { desc = "Equalize Split Window Size" })
map("n", "<leader>wx", "<cmd>close<CR>", { desc = "Close Current Window" })
map("n", "<leader>wl", "<C-w>l", { desc = "Next Window" })
map("n", "<leader>wh", "<C-w>h", { desc = "Prev Window" })
map("n", "<leader>wr", "<cmd>e %<CR>", { desc = "Reload Current Window" })
map("n", "<leader>wz", "<cmd>ZenMode<CR>", { desc = "Toggle Zen Mode" })

map("n", "<leader><Tab><Tab>", "<cmd>tabnew<CR>", { desc = "New Tab" })
map("n", "<leader><Tab>x", "<cmd>tabclose<CR>", { desc = "Close Current Tab" })
map("n", "<leader><Tab>l", "<cmd>tabn<CR>", { desc = "Next Tab" })
map("n", "<leader><Tab>h", "<cmd>tabp<CR>", { desc = "Prev Tab" })
map("n", "<leader><Tab>w", "<cmd>tabnew %<CR>", { desc = "Open Current Window in Tab" })

-- Substitute the word under the cursor, or the clipboard's text: the command line is filled in up
-- to the replacement.
map("n", "<leader>rw", ":%s/<C-r><C-w>//g<left><left>", { desc = "Rename Word (Window)" })
map("n", "<leader>rW", function()
  return ":" .. vim.fn.line(".") .. "s/<C-r><C-w>//g<left><left>"
end, { expr = true, desc = "Rename Word (Line)" })
map("n", "<leader>rc", function()
  return ":%s/" .. vim.fn.getreg("*") .. "//gc<left><left><left>"
end, { expr = true, desc = "Rename Clipboard Sequence (Window)" })
map("n", "<leader>rC", function()
  return ":" .. vim.fn.line(".") .. "s/" .. vim.fn.getreg("*") .. "//g<left><left>"
end, { expr = true, desc = "Rename Clipboard Sequence (Line)" })

map("n", "<leader>cH", function()
  vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled({}))
end, { desc = "Toggle Inlay Hints" })

-- Themes: 'background' picks Catppuccin's flavour.
map("n", "<leader>tl", function()
  vim.o.background = "light"
end, { desc = "Switch to Light Theme" })
map("n", "<leader>td", function()
  vim.o.background = "dark"
end, { desc = "Switch to Dark Theme" })
map("n", "<leader>tt", function()
  vim.o.background = vim.o.background == "dark" and "light" or "dark"
end, { desc = "Toggle Inverted Theme" })
map("n", "<leader>ts", "<cmd>Telescope colorscheme<CR>", { desc = "Find Theme" })
