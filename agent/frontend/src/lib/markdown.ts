
/**
 * Markdown渲染工具模块
 * 使用marked库解析Markdown，highlight.js实现代码高亮，dompurify防止XSS攻击
 */
import { marked, type MarkedExtension, type Tokens } from 'marked';
import hljs from 'highlight.js';
import DOMPurify from 'dompurify';

/**
 * 初始化marked配置和自定义renderer
 * 自定义renderer以控制输出格式，避免产生过多空行
 */
const setupMarked = (): void => {
  // 创建自定义renderer
  const renderer: MarkedExtension['renderer'] = {
    // 自定义标题渲染
    heading({ tokens, depth }: Tokens.Heading): string {
      const text = this.parser.parseInline(tokens);
      return `<h${depth} class="md-heading md-h${depth}">${text}</h${depth}>`;
    },

    // 自定义段落渲染
    paragraph({ tokens }: Tokens.Paragraph): string {
      const text = this.parser.parseInline(tokens);
      return `<p class="md-paragraph">${text}</p>`;
    },

    // 自定义代码块渲染
    code({ text, lang }: Tokens.Code): string {
      // 尝试用highlight.js高亮代码
      let highlightedCode = text;
      if (lang && hljs.getLanguage(lang)) {
        try {
          highlightedCode = hljs.highlight(text, { language: lang }).value;
        } catch (e) {
          // 如果高亮失败，使用原始文本
        }
      } else {
        try {
          highlightedCode = hljs.highlightAuto(text).value;
        } catch (e) {
          // 如果自动检测失败，使用原始文本
        }
      }

      const languageClass = lang ? `language-${lang}` : '';
      return `<pre class="md-code-block"><code class="${languageClass}">${highlightedCode}</code></pre>`;
    },

    // 自定义行内代码渲染
    codespan({ text }: Tokens.Codespan): string {
      return `<code class="md-inline-code">${text}</code>`;
    },

    // 自定义列表渲染
    list({ ordered, start, items }: Tokens.List): string {
      const tag = ordered ? 'ol' : 'ul';
      const startAttr = ordered && start !== 1 ? ` start="${start}"` : '';
      const listItems = items
        .map((item) => {
          const itemText = this.parser.parse(item.tokens);
          return `<li class="md-list-item">${itemText}</li>`;
        })
        .join('');
      return `<${tag} class="md-list ${ordered ? 'md-ordered-list' : 'md-unordered-list'}"${startAttr}>${listItems}</${tag}>`;
    },

    // 自定义链接渲染，添加安全属性
    link({ href, title, tokens }: Tokens.Link): string {
      const text = this.parser.parseInline(tokens);
      const titleAttr = title ? ` title="${title}"` : '';
      // 添加rel属性防止钓鱼攻击和安全漏洞
      return `<a href="${href}"${titleAttr} class="md-link" target="_blank" rel="noopener noreferrer">${text}</a>`;
    },

    // 自定义引用块渲染
    blockquote({ tokens }: Tokens.Blockquote): string {
      const text = this.parser.parse(tokens);
      return `<blockquote class="md-blockquote">${text}</blockquote>`;
    },

    // 自定义水平线渲染
    hr(): string {
      return '<hr class="md-hr">';
    },

    // 自定义表格渲染
    table({ header, rows }: Tokens.Table): string {
      const headerRow = header
        .map((cell) => {
          const text = this.parser.parseInline(cell.tokens);
          return `<th class="md-table-header">${text}</th>`;
        })
        .join('');

      const bodyRows = rows
        .map((row) => {
          const cells = row
            .map((cell) => {
              const text = this.parser.parseInline(cell.tokens);
              return `<td class="md-table-cell">${text}</td>`;
            })
            .join('');
          return `<tr class="md-table-row">${cells}</tr>`;
        })
        .join('');

      return `<table class="md-table"><thead><tr>${headerRow}</tr></thead><tbody>${bodyRows}</tbody></table>`;
    },

    // 自定义图像渲染
    image({ href, title, text }: Tokens.Image): string {
      const titleAttr = title ? ` title="${title}"` : '';
      const altAttr = text ? ` alt="${text}"` : '';
      return `<img src="${href}"${altAttr}${titleAttr} class="md-image">`;
    },
  };

  // 配置marked
  marked.use({
    renderer,
    breaks: true, // 支持\n换行
    gfm: true, // 支持GitHub Flavored Markdown
  });
};

// 初始化marked配置
setupMarked();

/**
 * 将Markdown文本转换为安全的HTML
 * @param markdown - 原始Markdown文本
 * @returns 经过XSS过滤的HTML字符串
 */
export function renderMarkdown(markdown: string): string {
  if (!markdown || typeof markdown !== 'string') {
    return '';
  }

  // 预处理Markdown，合并过多的空行
  // 将3个或更多连续换行替换为2个换行
  const preprocessed = markdown.replace(/\n{3,}/g, '\n\n');

  // 使用marked解析Markdown
  let html = marked.parse(preprocessed) as string;

  // 使用DOMPurify进行XSS过滤
  // 配置允许的标签和属性
  const purifyConfig = {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'strong', 'em', 'u', 's', 'del',
      'code', 'pre',
      'ul', 'ol', 'li',
      'a', 'img',
      'blockquote',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'span', 'div',
    ],
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title',
      'class', 'id',
      'target', 'rel',
      'start', // 用于有序列表的start属性
    ],
    FORBID_TAGS: ['script', 'style', 'iframe', 'form'],
    FORBID_ATTR: ['onclick', 'onload', 'onerror', 'style'],
  };

  html = DOMPurify.sanitize(html, purifyConfig);

  return html;
}

/**
 * 导出DOMPurify实例，供其他地方使用
 */
export { DOMPurify };

/**
 * 导出highlight.js实例，供自定义使用
 */
export { hljs };
