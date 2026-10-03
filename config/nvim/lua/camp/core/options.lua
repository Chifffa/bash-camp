-- Editor options.

local opt = vim.opt

opt.number = true
opt.relativenumber = true
opt.cursorline = true
opt.signcolumn = "yes"
opt.wrap = false

opt.tabstop = 2
opt.shiftwidth = 2
opt.expandtab = true
opt.autoindent = true
opt.backspace = "indent,eol,start"

-- Searches ignore case until the pattern has a capital.
opt.ignorecase = true
opt.smartcase = true

opt.termguicolors = true
opt.background = "dark"
opt.splitright = true
opt.splitbelow = true
opt.termsync = true

-- Yanks and pastes go through the system clipboard.
opt.clipboard:append("unnamedplus")

-- Without a desktop session - over ssh, on a console, in a container - only the terminal can reach
-- the clipboard, through OSC 52. Inside tmux, Neovim's own choice stands: tmux's buffers, or xclip
-- where there is a display.
local desktop = vim.env.XDG_SESSION_TYPE ~= nil and vim.env.XDG_SESSION_TYPE ~= "tty"
if (vim.env.SSH_TTY or not desktop) and not vim.env.TMUX then
  local osc52 = require("vim.ui.clipboard.osc52")
  vim.g.clipboard = {
    name = "OSC 52",
    copy = { ["+"] = osc52.copy("+"), ["*"] = osc52.copy("*") },
    paste = { ["+"] = osc52.paste("+"), ["*"] = osc52.paste("*") },
  }
end
