import com.github.javaparser.Position;
import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseException;
import com.github.javaparser.ParseProblemException;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.NodeList;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.comments.Comment;
import com.github.javaparser.ast.ImportDeclaration;
import com.github.javaparser.ast.PackageDeclaration;
import com.github.javaparser.ast.body.VariableDeclarator;

// LiteralStringValueExpr, DoubleLiteralExpr, IntegerLiteralExpr, CharLiteralExpr
// StringLiteralExpr, BooleanLiteralExpr, NullLiteralExpr, MethodCallExpr
import com.github.javaparser.ast.expr.*;

import com.github.javaparser.symbolsolver.javaparsermodel.JavaParserFacade;
import com.github.javaparser.symbolsolver.resolution.typesolvers.CombinedTypeSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.ReflectionTypeSolver;

import java.util.ArrayList;
import java.util.Collections;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class CodeParser {

    int wrapUsed;
    final String[] wrapStart = { "", "class SampleClass {", "class SampleClass {\nvoid SampleMethod() {" };
    final String[] wrapEnd = { "", "\n}", "\n}\n}" };

    private class Entry implements Comparable<Entry> {
        String name;
        Position position;

        Entry(String name, Position position) {
            this.name = name;
            this.position = position;
        }

        public Position getPosition() {
            return this.position;
        }

        @Override
        public int compareTo(Entry otherEntry) {
            Position otherPosition = otherEntry.getPosition();
            return position.compareTo(otherPosition);
        }

        @Override
        public String toString() {
            return "[" + position.line + "," + position.column + "]: " + name;
        }
    }

    public String extractCodeInfo(String inputCode, boolean keepImports, boolean keepComments, boolean keepLiterals) {
        ArrayList<String> entries = new ArrayList<String>();
        ArrayList<Entry> entries_list = new ArrayList<Entry>();

        // Minimal type solver that only looks at the classes used to run this sample.
        CombinedTypeSolver typeSolver = new CombinedTypeSolver();
        typeSolver.add(new ReflectionTypeSolver());

        // Parse code
        CompilationUnit cu = parseCodeSnippet(inputCode);
        if (cu == null) {
            return "__ERROR__";
        }

        // Extract imports
        if (keepImports) {
            for (ImportDeclaration im : cu.getImports()) {
                String name = im.getName().asString();
                Position position = im.getBegin().orElse(null);
                entries_list.add(new Entry("_IM_" + name, position));
            }
        }

        // Extract comments
        if (keepComments) {
            for (Comment c : cu.getComments()) {
                String name = c.getContent().trim().replaceAll(",", " ").replaceAll("\\s+", " ");
                if (!name.startsWith("TODO Auto-generated")) {
                    Position position = c.getBegin().orElse(null);
                    entries_list.add(new Entry("_COM_" + name, position));
                }
            }
        }

        // Extract variable declarations/literals
        if (keepLiterals) {
            cu.findAll(VariableDeclarationExpr.class).forEach(vd -> {
                for (VariableDeclarator var : vd.getVariables()) {
                    String name = var.getType().asString().trim();
                    Position position = var.getBegin().orElse(null);
                    entries_list.add(new Entry("_VD_" + name, position));
                }
            });
        }

        // Extract object creations
        cu.findAll(ObjectCreationExpr.class).forEach(oc -> {
            String name = oc.getType().asString().trim();
            Position position = oc.getBegin().orElse(null);
            entries_list.add(new Entry("_OC_" + name, position));
        });

        // Extract method invocations
        cu.findAll(MethodCallExpr.class).forEach(mc -> {
            Position position = mc.getBegin().orElse(null);
            try {
                String qualifiedName = JavaParserFacade.get(typeSolver).solveMethodAsUsage(mc).getDeclaration()
                        .getQualifiedName().trim();
                String[] slices = qualifiedName.split("\\.");
                String methodName = slices[slices.length - 1];
                String objectName = slices[slices.length - 2];

                if (!methodName.equals("print") && !methodName.equals("println")
                        && !methodName.equals("printStackTrace")) {

                    String name = objectName + "." + methodName;
                    entries_list.add(new Entry("_MC_" + name, position));
                }
            } catch (Exception e) {
                String methodName = mc.getName().asString();
                String[] exc = e.getMessage().replaceAll("\\s+", "").split(":");

                if (exc.length == 2) {
                    String objectName = exc[1];
                    entries_list.add(new Entry("_MC_" + objectName + "." + methodName, position));
                } else {
                    entries_list.add(new Entry("_MC_" + methodName, position));
                }
            }
        });

        // Sort on line and column number
        Collections.sort(entries_list);
        // Get api names
        entries = entries_list.stream().map(obj -> new String(obj.name)).collect(ArrayList::new, ArrayList::add,
                ArrayList::addAll);

        return String.join(", ", entries);
    }

    public String parseCode(String inputCode, boolean keepImports, boolean keepComments, boolean keepLiterals) {
        CompilationUnit cu = parseCodeSnippet(inputCode);
        if (cu == null) {
            return "__ERROR__";
        }
        if (!keepImports) {
            // Remove PackageDeclaration
            cu.getPackageDeclaration().ifPresent(p -> p.remove());
            // Remove ImportDeclarations
            cu.getImports().removeIf(i -> true);
        }
        if (!keepComments) {
            cu.getComments().forEach(c -> c.remove());
        }
        if (!keepLiterals) {
            cu.findAll(LiteralExpr.class).forEach(l -> l.replace(replaceLiteralType(l)));
        }

        String parsedCode = cu.toString().trim();
        switch (wrapUsed) {
        case 1:
            parsedCode = parsedCode.replace("class SampleClass {", "");
            parsedCode = parsedCode.substring(0, parsedCode.length() - 1).trim();
            parsedCode = parsedCode.replaceAll("(?m)^ {1,4}", "");
            break;
        case 2:
            parsedCode = parsedCode.replace("class SampleClass {", "");
            parsedCode = parsedCode.replace("void SampleMethod() {", "");
            parsedCode = parsedCode.substring(0, parsedCode.length() - 3).trim();
            parsedCode = parsedCode.replaceAll("(?m)^ {1,}", "");
            break;
        }
        return parsedCode;
    }

    private CompilationUnit parseCodeSnippet(String codeSnippet) {
        for (int i = 0; i < wrapStart.length; i++) {
            try {
                String wrappedCodeSnippet = wrapStart[i] + codeSnippet + wrapEnd[i];
                CompilationUnit cu = JavaParser.parse(wrappedCodeSnippet);
                wrapUsed = i;
                return cu;
            } catch (Exception e) {
                continue;
            }
        }
        wrapUsed = 0;
        return null;
    }

    private NameExpr replaceLiteralType(LiteralExpr literal) {
        if (literal instanceof LiteralStringValueExpr) {
            if (literal instanceof CharLiteralExpr) {
                return new NameExpr("__char__");
            } else if (literal instanceof DoubleLiteralExpr) {
                return new NameExpr("__double__");
            } else if (literal instanceof IntegerLiteralExpr) {
                return new NameExpr("__integer__");
            } else if (literal instanceof LongLiteralExpr) {
                return new NameExpr("__long__");
            } else if (literal instanceof StringLiteralExpr) {
                return new NameExpr("__string__");
            }
        } else if (literal instanceof BooleanLiteralExpr) {
            return new NameExpr("__boolean__");
        } else if (literal instanceof NullLiteralExpr) {
            return new NameExpr("null");
        }

        return new NameExpr("unk");
    }
}