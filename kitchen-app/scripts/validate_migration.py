#!/usr/bin/env python3
"""
Migration Validation Script

This script helps validate the new BOM system by:
1. Checking recipe coverage for all cabinet types
2. Comparing old vs new costs
3. Identifying missing recipes
4. Generating validation report

Run with: uv run python scripts/validate_migration.py
"""

import sys
from pathlib import Path
from sqlmodel import Session, select, func
from kitchen_erp.database import get_session, create_db_and_tables
from kitchen_erp.models import Cabinet, Project, ProjectDefaults
from kitchen_erp.bom_generator import BOMGenerator
from kitchen_erp.recipe_loader import load_recipes


def check_recipe_coverage():
    """Check if all cabinet types in database have recipes"""
    print("\n" + "="*70)
    print("STEP 1: Recipe Coverage Check")
    print("="*70)
    
    with next(get_session()) as session:
        # Get all unique module_kind values
        module_kinds = session.exec(
            select(Cabinet.module_kind).distinct()
        ).all()
        
        if not module_kinds:
            print("⚠️  No cabinets found in database")
            print("   Create a test project first using the UI")
            return False
        
        print(f"\nFound {len(module_kinds)} cabinet types in database:")
        
        # Load recipes
        try:
            recipes = load_recipes()
        except FileNotFoundError:
            print("❌ recipes.json not found!")
            return False
        
        # Check coverage
        missing = []
        for mk in module_kinds:
            count = session.exec(
                select(func.count(Cabinet.id)).where(Cabinet.module_kind == mk)
            ).one()
            
            has_recipe = mk in recipes
            status = "✅" if has_recipe else "❌"
            print(f"  {status} {mk}: {count} cabinets")
            
            if not has_recipe:
                missing.append(mk)
        
        if missing:
            print(f"\n❌ Missing recipes for: {', '.join(missing)}")
            print("\nTo fix:")
            print("  1. Open kitchen_erp/recipes.json")
            print("  2. Add entries for missing types (copy existing recipe as template)")
            print("  3. Run this script again")
            return False
        else:
            print("\n✅ All cabinet types have recipes!")
            return True


def compare_costs():
    """Compare old vs new BOM costs for all projects"""
    print("\n" + "="*70)
    print("STEP 2: Cost Comparison (Old vs New)")
    print("="*70)
    
    with next(get_session()) as session:
        projects = session.exec(select(Project)).all()
        
        if not projects:
            print("⚠️  No projects found in database")
            return True
        
        print(f"\nAnalyzing {len(projects)} project(s)...\n")
        
        all_match = True
        
        for project in projects:
            if not project.cabinets:
                continue
            
            defaults = session.exec(
                select(ProjectDefaults).where(
                    ProjectDefaults.project_id == project.id
                )
            ).first()
            
            if not defaults:
                print(f"⚠️  Project '{project.customer_name}' has no defaults")
                continue
            
            print(f"Project: {project.customer_name}")
            print("-" * 70)
            print(f"{'Cabinet':<30} {'Old Cost':<12} {'New Cost':<12} {'Diff':<10} {'%':<8}")
            print("-" * 70)
            
            for cabinet in project.cabinets:
                try:
                    # OLD SYSTEM
                    old_result = cabinet.calculate_cost(defaults, waste_factor=1.20)
                    old_cost = old_result.total_cost
                    
                    # NEW SYSTEM
                    generator = BOMGenerator(cabinet, defaults)
                    bom_tree = generator.generate()
                    new_cost = bom_tree.cost
                    
                    # Compare
                    diff = new_cost - old_cost
                    diff_pct = (diff / old_cost * 100) if old_cost > 0 else 0
                    
                    # Status
                    if abs(diff_pct) < 10:
                        status = "✅"
                    elif abs(diff_pct) < 20:
                        status = "⚠️ "
                        all_match = False
                    else:
                        status = "❌"
                        all_match = False
                    
                    print(f"{status} {cabinet.name[:28]:<30} "
                          f"${old_cost:>10.2f} ${new_cost:>10.2f} "
                          f"${diff:>8.2f} {diff_pct:>6.1f}%")
                
                except Exception as e:
                    print(f"❌ {cabinet.name[:28]:<30} ERROR: {str(e)}")
                    all_match = False
            
            print()
        
        if all_match:
            print("✅ All costs within 10% tolerance")
        else:
            print("⚠️  Some costs differ by >10%")
            print("\nThis is often expected because:")
            print("  • New system uses purchasing strategies (full sheets)")
            print("  • New system includes tag-based hardware")
            print("  • New system is more accurate")
            print("\nReview differences and verify they make sense")
        
        return all_match


def generate_report():
    """Generate detailed validation report"""
    print("\n" + "="*70)
    print("STEP 3: Generating Validation Report")
    print("="*70)
    
    report_path = Path("validation_report.txt")
    
    with open(report_path, "w") as f:
        f.write("BOM SYSTEM MIGRATION VALIDATION REPORT\n")
        f.write("="*70 + "\n\n")
        
        # Recipe coverage
        f.write("1. RECIPE COVERAGE\n")
        f.write("-"*70 + "\n")
        
        with next(get_session()) as session:
            module_kinds = session.exec(
                select(Cabinet.module_kind).distinct()
            ).all()
            
            recipes = load_recipes()
            
            for mk in module_kinds:
                count = session.exec(
                    select(func.count(Cabinet.id)).where(Cabinet.module_kind == mk)
                ).one()
                
                has_recipe = mk in recipes
                status = "OK" if has_recipe else "MISSING"
                f.write(f"  {mk}: {count} cabinets - {status}\n")
        
        # Cost comparison
        f.write("\n2. COST COMPARISON\n")
        f.write("-"*70 + "\n")
        
        with next(get_session()) as session:
            projects = session.exec(select(Project)).all()
            
            for project in projects:
                if not project.cabinets:
                    continue
                
                defaults = session.exec(
                    select(ProjectDefaults).where(
                        ProjectDefaults.project_id == project.id
                    )
                ).first()
                
                if not defaults:
                    continue
                
                f.write(f"\nProject: {project.customer_name}\n")
                
                for cabinet in project.cabinets:
                    try:
                        old_result = cabinet.calculate_cost(defaults, waste_factor=1.20)
                        generator = BOMGenerator(cabinet, defaults)
                        bom_tree = generator.generate()
                        
                        diff = bom_tree.cost - old_result.total_cost
                        diff_pct = (diff / old_result.total_cost * 100) if old_result.total_cost > 0 else 0
                        
                        f.write(f"  {cabinet.name}: ${old_result.total_cost:.2f} → ${bom_tree.cost:.2f} "
                               f"({diff_pct:+.1f}%)\n")
                    except Exception as e:
                        f.write(f"  {cabinet.name}: ERROR - {str(e)}\n")
        
        # Recommendations
        f.write("\n3. RECOMMENDATIONS\n")
        f.write("-"*70 + "\n")
        f.write("  • Review cost differences >10%\n")
        f.write("  • Verify purchasing strategies match supplier pricing\n")
        f.write("  • Add missing recipes if any\n")
        f.write("  • Proceed to Phase 2 (UI Integration) when ready\n")
    
    print(f"\n✅ Report saved to: {report_path.absolute()}")
    print("\nNext steps:")
    print("  1. Review validation_report.txt")
    print("  2. Fix any issues found")
    print("  3. Re-run this script until all checks pass")
    print("  4. Proceed to Phase 2 (see MIGRATION_GUIDE.md)")


def main():
    """Run all validation checks"""
    print("\n" + "="*70)
    print("BOM SYSTEM MIGRATION VALIDATION")
    print("="*70)
    print("\nThis script validates the new BOM system before UI migration.")
    print("It will:")
    print("  1. Check recipe coverage")
    print("  2. Compare old vs new costs")
    print("  3. Generate validation report")
    
    # Ensure database exists
    try:
        create_db_and_tables()
    except Exception as e:
        print(f"\n❌ Database error: {e}")
        return 1
    
    # Run checks
    recipe_ok = check_recipe_coverage()
    
    if not recipe_ok:
        print("\n❌ Validation failed: Missing recipes")
        print("Fix recipe coverage issues before proceeding")
        return 1
    
    cost_ok = compare_costs()
    
    # Always generate report
    generate_report()
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    if recipe_ok and cost_ok:
        print("✅ All validation checks passed!")
        print("\nYou can proceed to Phase 2 (UI Integration)")
        print("See MIGRATION_GUIDE.md for next steps")
        return 0
    else:
        print("⚠️  Some validation checks need attention")
        print("\nReview the issues above and validation_report.txt")
        print("Fix issues and re-run this script")
        return 1


if __name__ == "__main__":
    sys.exit(main())
