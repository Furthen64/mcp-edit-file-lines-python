from pathlib import Path

FIXTURES = {
    "test-edits.txt": """line 1: function hello() {
line 2:   console.log(\"Hello\");
line 3: }
line 4: 
line 5: function world() {
line 6:   return \"World\";
line 7: }
line 8:
line 9: module.exports = {
line 10:   hello,
line 11:   world
line 12: };\n""",
    "test-matches.txt": """// Basic component with props
const Button = ({ color = \"blue\", size = \"md\" }) => {
  return <button className={`btn-${color} size-${size}`}>Click me</button>;
};

// Component with multiple props and nested structure
export const Card = ({
  title,
  subtitle = \"Default subtitle\",
  theme = \"light\",
  size = \"lg\",
}) => {
  const cardClass = `card-${theme} size-${size}`;
  
  return (
    <div className={cardClass}>
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  );
};

// Constants and configurations
const THEME = {
  light: { bg: \"#ffffff\", text: \"#000000\" },
  dark: { bg: \"#000000\", text: \"#ffffff\" },
};

const CONFIG = {
  apiUrl: \"https://api.example.com\",
  timeout: 5000,
  retries: 3,
};\n""",
    "sample.txt": """line 1
line 2
line 3
line 4
line 5
""",
}


def reset_fixtures() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    for name, content in FIXTURES.items():
        (fixtures_dir / name).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    reset_fixtures()
