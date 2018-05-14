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

public class CodeParser {

    private static final String[] wrapStart = { "", "class SampleClass {",
            "class SampleClass {\nvoid SampleMethod() {" };
    private static final String[] wrapEnd = { "", "\n}", "\n}\n}" };

    private static class WrappedCompilationUnit {
        private final int wrap;
        private final CompilationUnit cu;

        WrappedCompilationUnit(int wrap, CompilationUnit cu) {
            this.wrap = wrap;
            this.cu = cu;
        }

        public int getWrap() {
            return wrap;
        }

        public CompilationUnit getCu() {
            return cu;
        }
    }

    private static class Entry implements Comparable<Entry> {
        private final String name;
        private final Position position;

        Entry(String name, Position position) {
            this.name = name;
            this.position = position;
        }

        public String getName() {
            return name;
        }

        public Position getPosition() {
            return position;
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

    public static String extractCodeInfo(String inputCode, boolean keepImports, boolean keepComments,
            boolean keepLiterals, boolean keepUnknownMethodCalls) {
        ArrayList<String> entries = new ArrayList<String>();
        ArrayList<Entry> entries_list = new ArrayList<Entry>();

        // Minimal type solver that only looks at the classes used to run this sample.
        CombinedTypeSolver typeSolver = new CombinedTypeSolver();
        typeSolver.add(new ReflectionTypeSolver());

        // Parse code
        CompilationUnit cu = parseCodeSnippet(inputCode).cu;
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

        // Extract literals and objects from FieldDeclarations, VariableDeclarationExpr
        if (keepLiterals) {
            cu.findAll(VariableDeclarator.class).forEach(vd -> {
                String name = vd.getType().asString().trim();
                Position position = vd.getBegin().orElse(null);
                entries_list.add(new Entry("_VAR_" + name, position));
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
                } else if (keepUnknownMethodCalls) {
                    entries_list.add(new Entry("_UMC_" + methodName, position));
                }
            }
        });

        // Sort entries on their position
        Collections.sort(entries_list);
        // Get entry names
        entries = entries_list.stream().map(obj -> new String(obj.getName())).collect(ArrayList::new, ArrayList::add,
                ArrayList::addAll);

        return String.join(", ", entries);
    }

    public static String parseCode(String inputCode, boolean keepImports, boolean keepComments, boolean keepLiterals) {
        WrappedCompilationUnit wrappedCU = parseCodeSnippet(inputCode);
        CompilationUnit cu = wrappedCU.cu;
        int wrapUsed = wrappedCU.wrap;

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

    private static WrappedCompilationUnit parseCodeSnippet(String codeSnippet) {
        for (int i = 0; i < wrapStart.length; i++) {
            try {
                String wrappedCodeSnippet = wrapStart[i] + codeSnippet + wrapEnd[i];
                CompilationUnit cu = JavaParser.parse(wrappedCodeSnippet);
                return new WrappedCompilationUnit(i, cu);
            } catch (Exception e) {
                continue;
            }
        }
        return new WrappedCompilationUnit(0, null);
    }

    private static NameExpr replaceLiteralType(LiteralExpr literal) {
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